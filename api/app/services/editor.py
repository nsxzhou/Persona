"""Editor AI service — encapsulates all LLM-powered editor operations.

Streaming methods are *regular* async functions that eagerly read ORM data
(and pre-build the LLM model) while the DB session is still alive, then
return a lightweight async generator that only references plain Python
values.  This eliminates the ORM-detach risk present when an async
generator is iterated inside a ``StreamingResponse`` after the session
dependency has been torn down.
"""

from __future__ import annotations

import logging
import re
import json
from collections.abc import AsyncGenerator

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain_errors import BadRequestError
from app.core.length_presets import LENGTH_PRESETS, get_progress
from app.schemas.editor import (
    BeatExpandRequest,
    BeatGenerateRequest,
    BibleUpdateRequest,
    ConceptGenerateRequest,
    EditorCompletionRequest,
    SectionGenerateRequest,
    VolumeChaptersRequest,
    VolumeGenerateRequest,
)
from app.schemas.projects import ConceptItem
from app.services.context_assembly import (
    WritingContextSections,
    assemble_writing_context,
)
from app.schemas.prompt_profiles import (
    GenerationProfile,
    build_chapter_objective_card,
    build_intensity_profile,
)
from app.services.editor_prompts import (
    VALID_SECTIONS,
    build_active_characters_system_prompt,
    build_active_characters_user_message,
    build_beat_expand_system_prompt,
    build_beat_expand_user_message,
    build_beat_generate_system_prompt,
    build_beat_generate_user_message,
    build_bible_update_system_prompt,
    build_bible_update_user_message,
    build_concept_generate_system_prompt,
    build_concept_generate_user_message,
    build_section_system_prompt,
    build_section_user_message,
    build_volume_generate_system_prompt,
    build_volume_generate_user_message,
    build_volume_chapters_system_prompt,
    build_volume_chapters_user_message,
    parse_bible_update_response,
    parse_concept_response,
)
from app.services.llm_provider import LLMProviderService
from app.services.outline_parser import parse_outline
from app.services.plot_profiles import PlotProfileService
from app.services.prompt_injection_policy import PromptInjectionTask
from app.services.projects import ProjectService
from app.services.provider_configs import ProviderConfigService
from app.services.style_profiles import StyleProfileService

logger = logging.getLogger(__name__)

_BEAT_PREFIX_RE = re.compile(r"^[\d]+[.、)\]\s]+|^[-*+]\s+")


class _EditorServiceBase:
    def __init__(
        self,
        llm_service: LLMProviderService | None = None,
        project_service: ProjectService | None = None,
        style_profile_service: StyleProfileService | None = None,
        plot_profile_service: PlotProfileService | None = None,
        provider_config_service: ProviderConfigService | None = None,
    ) -> None:
        self.llm_service = llm_service or LLMProviderService()
        self.project_service = project_service or ProjectService()
        self.style_profile_service = style_profile_service or StyleProfileService()
        self.plot_profile_service = plot_profile_service or PlotProfileService()
        self.provider_config_service = provider_config_service or ProviderConfigService()

    async def _get_style_prompt(
        self,
        session: AsyncSession,
        project,
        user_id: str,
    ) -> str | None:
        """Return the style prompt_pack_payload for the project, or *None*."""
        return await self._get_style_prompt_by_id(session, project.style_profile_id, user_id)

    async def _get_plot_prompt(
        self,
        session: AsyncSession,
        project,
        user_id: str,
    ) -> str | None:
        return await self._get_plot_prompt_by_id(session, project.plot_profile_id, user_id)

    async def _get_style_prompt_by_id(
        self,
        session: AsyncSession,
        style_profile_id: str | None,
        user_id: str,
    ) -> str | None:
        if not style_profile_id:
            return None
        style_profile = await self.style_profile_service.get_or_404(
            session,
            style_profile_id,
            user_id=user_id,
        )
        return style_profile.prompt_pack_payload

    async def _get_plot_prompt_by_id(
        self,
        session: AsyncSession,
        plot_profile_id: str | None,
        user_id: str,
    ) -> str | None:
        if not plot_profile_id:
            return None
        plot_profile = await self.plot_profile_service.get_or_404(
            session,
            plot_profile_id,
            user_id=user_id,
        )
        return plot_profile.prompt_pack_payload

    def _require_generation_profile(
        self,
        *,
        explicit_profile: GenerationProfile | None,
        project=None,
    ) -> GenerationProfile:
        if explicit_profile is not None:
            return explicit_profile
        if project is not None and getattr(project, "generation_profile_payload", None) is not None:
            return GenerationProfile.model_validate(project.generation_profile_payload)
        raise BadRequestError("项目未配置 generation_profile，无法进行正式生成")

    async def _extract_active_characters(
        self,
        provider_config: dict | None,
        text_before_cursor: str,
        current_chapter_context: str,
    ) -> list[str]:
        if not provider_config:
            return []
        
        system_prompt = build_active_characters_system_prompt()
        user_message = build_active_characters_user_message(text_before_cursor, current_chapter_context)
        
        raw_response = await self.llm_service.invoke_completion(
            provider_config=provider_config,
            system_prompt=system_prompt,
            user_context=user_message,
            injection_task=PromptInjectionTask.EDITOR_BEAT_EXPANSION, # Use an existing or a new appropriate task, using BEAT_EXPANSION as fallback.
        )
        
        try:
            # Simple heuristic to extract JSON array
            match = re.search(r"\[.*\]", raw_response, flags=re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, list):
                    return [str(name) for name in parsed]
            return []
        except Exception as e:
            logging.warning(f"Failed to parse active characters JSON: {e}")
            return []

    def _build_dynamic_character_panel(
        self,
        characters_blueprint: str,
        characters_status: str,
        active_names: list[str],
    ) -> tuple[str, str]:
        if not active_names:
            return "", ""
            
        def _extract_character_section(markdown: str, names: list[str]) -> str:
            if not markdown.strip():
                return ""
                
            parts = re.split(r"(?m)^(#{2,3}\s+.*)$", markdown)
            extracted = []
            current_name_matches = False
            
            for i in range(len(parts)):
                part = parts[i]
                if part.startswith("##"):
                    current_name_matches = any(name.lower() in part.lower() for name in names)
                    if current_name_matches:
                        extracted.append(part.strip())
                elif current_name_matches and part.strip():
                    extracted.append(part.strip())
                    
            return "\n\n".join(extracted)

        active_blueprint = _extract_character_section(characters_blueprint, active_names)
        active_status = _extract_character_section(characters_status, active_names)
        
        return active_blueprint, active_status


class WritingEditorService(_EditorServiceBase):
    async def stream_completion(
        self,
        session: AsyncSession,
        project_id: str,
        user_id: str,
        payload: EditorCompletionRequest,
    ) -> AsyncGenerator[str, None]:
        project = await self.project_service.get_or_404(
            session, project_id, user_id=user_id,
        )
        bible = await self.project_service.get_bible_or_404(
            session, project_id, user_id=user_id,
        )
        if not project.style_profile_id:
            raise BadRequestError("项目未挂载风格档案")

        style_profile = await self.style_profile_service.get_or_404(
            session,
            project.style_profile_id,
            user_id=user_id,
        )
        plot_prompt = await self._get_plot_prompt(session, project, user_id)
        generation_profile = self._require_generation_profile(
            explicit_profile=payload.generation_profile,
            project=project,
        )
        
        active_names = await self._extract_active_characters(
            project.provider,
            payload.text_before_cursor,
            payload.current_chapter_context,
        )
        active_blueprint, active_status = self._build_dynamic_character_panel(
            bible.characters_blueprint,
            bible.characters_status,
            active_names,
        )

        chapter_objective_card = build_chapter_objective_card(
            generation_profile,
            current_chapter_context=payload.current_chapter_context,
            outline_detail=bible.outline_detail,
        )
        system_prompt = assemble_writing_context(
            voice_profile_markdown=style_profile.prompt_pack_payload,
            story_engine_markdown=plot_prompt,
            generation_profile=generation_profile,
            intensity_profile=build_intensity_profile(generation_profile),
            chapter_objective_card=chapter_objective_card,
            sections=WritingContextSections(
                description=project.description,
                world_building=bible.world_building,
                characters_blueprint=active_blueprint or bible.characters_blueprint, # Fallback if empty
                outline_master=bible.outline_master,
                outline_detail=bible.outline_detail,
                characters_status=active_status or bible.characters_status,
                runtime_state=bible.runtime_state,
                runtime_threads=bible.runtime_threads,
            ),
            length_preset=project.length_preset,
            content_length=payload.total_content_length,
        )
        user_context_parts: list[str] = []
        if payload.previous_chapter_context.strip():
            user_context_parts.append(
                f"## 前序章节\n\n{payload.previous_chapter_context}"
            )
        if payload.current_chapter_context.strip():
            user_context_parts.append(
                f"## 当前章节\n\n{payload.current_chapter_context}"
            )
        user_context_parts.append(
            "请从以下当前章节光标位置继续写作，保持自然衔接：\n\n"
            f"{payload.text_before_cursor}"
        )
        user_context = "\n\n---\n\n".join(user_context_parts)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_context),
        ]
        return self.llm_service.stream_messages(
            project.provider,
            messages,
            injection_task=PromptInjectionTask.EDITOR_CONTINUATION,
        )

    async def stream_section_generation(
        self,
        session: AsyncSession,
        project_id: str,
        user_id: str,
        payload: SectionGenerateRequest,
    ) -> AsyncGenerator[str, None]:
        if payload.section not in VALID_SECTIONS:
            raise BadRequestError(
                f"无效的区块名称：{payload.section}，"
                f"有效值为 {', '.join(sorted(VALID_SECTIONS))}"
            )

        project = await self.project_service.get_or_404(
            session, project_id, user_id=user_id,
        )

        style_prompt = await self._get_style_prompt(session, project, user_id)
        plot_prompt = await self._get_plot_prompt(session, project, user_id)
        generation_profile = self._require_generation_profile(
            explicit_profile=None,
            project=project,
        )

        regenerating = bool(payload.previous_output or payload.user_feedback)
        system_prompt = build_section_system_prompt(
            payload.section,
            style_prompt,
            plot_prompt,
            generation_profile=generation_profile,
            length_preset=project.length_preset,
            regenerating=regenerating,
        )
        user_message = build_section_user_message(
            payload.section,
            {
                "description": payload.description,
                "world_building": payload.world_building,
                "characters_blueprint": payload.characters_blueprint,
                "outline_master": payload.outline_master,
                "outline_detail": payload.outline_detail,
                "characters_status": payload.characters_status,
                "runtime_state": payload.runtime_state,
                "runtime_threads": payload.runtime_threads,
            },
            previous_output=payload.previous_output,
            user_feedback=payload.user_feedback,
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        return self.llm_service.stream_messages(
            project.provider,
            messages,
            injection_task=PromptInjectionTask.EDITOR_SECTION_GENERATION,
        )

    async def stream_beat_expansion(
        self,
        session: AsyncSession,
        project_id: str,
        user_id: str,
        payload: BeatExpandRequest,
    ) -> AsyncGenerator[str, None]:
        project = await self.project_service.get_or_404(
            session, project_id, user_id=user_id,
        )
        if not project.provider:
            raise BadRequestError("项目未配置 Provider，无法调用 AI")

        style_prompt = await self._get_style_prompt(session, project, user_id)
        plot_prompt = await self._get_plot_prompt(session, project, user_id)
        generation_profile = self._require_generation_profile(
            explicit_profile=None,
            project=project,
        )
        preset_cfg = LENGTH_PRESETS.get(project.length_preset, LENGTH_PRESETS["long"])

        regenerating = bool(payload.previous_output or payload.user_feedback)
        system_prompt = build_beat_expand_system_prompt(
            style_prompt,
            plot_prompt,
            generation_profile=generation_profile,
            beat_expand_chars=preset_cfg["beat_expand_chars"],
            regenerating=regenerating,
        )
        user_message = build_beat_expand_user_message(
            payload.text_before_cursor,
            payload.beat,
            payload.beat_index,
            payload.total_beats,
            payload.preceding_beats_prose,
            payload.outline_detail,
            payload.runtime_state,
            payload.runtime_threads,
            current_chapter_context=payload.current_chapter_context,
            previous_chapter_context=payload.previous_chapter_context,
            previous_output=payload.previous_output,
            user_feedback=payload.user_feedback,
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        return self.llm_service.stream_messages(
            project.provider,
            messages,
            injection_task=PromptInjectionTask.EDITOR_BEAT_EXPANSION,
        )


class MemoryEditorService(_EditorServiceBase):
    async def propose_bible_update(
        self,
        session: AsyncSession,
        project_id: str,
        user_id: str,
        payload: BibleUpdateRequest,
    ) -> tuple[str, str, str, str | None, bool]:
        project = await self.project_service.get_or_404(
            session, project_id, user_id=user_id,
        )
        if not project.provider:
            raise BadRequestError("项目未配置 Provider，无法调用 AI")

        import asyncio
        from app.prompts.editor import build_chapter_summary_system_prompt, build_chapter_summary_user_message

        regenerating = bool(payload.previous_output or payload.user_feedback)
        system_prompt = build_bible_update_system_prompt(regenerating=regenerating)
        user_message = build_bible_update_user_message(
            current_characters_status=payload.current_characters_status,
            current_runtime_state=payload.current_runtime_state,
            current_runtime_threads=payload.current_runtime_threads,
            content_to_check=payload.content_to_check,
            sync_scope=payload.sync_scope,
            previous_output=payload.previous_output,
            user_feedback=payload.user_feedback,
        )

        bible_update_task = self.llm_service.invoke_completion(
            provider_config=project.provider,
            system_prompt=system_prompt,
            user_context=user_message,
            injection_task=PromptInjectionTask.EDITOR_BIBLE_UPDATE,
        )

        if payload.sync_scope == "chapter_full":
            summary_system_prompt = build_chapter_summary_system_prompt()
            summary_user_message = build_chapter_summary_user_message(payload.content_to_check)
            summary_task = self.llm_service.invoke_completion(
                provider_config=project.provider,
                system_prompt=summary_system_prompt,
                user_context=summary_user_message,
                injection_task=PromptInjectionTask.EDITOR_CHAPTER_SUMMARY,
            )
            raw_bible, raw_summary = await asyncio.gather(bible_update_task, summary_task)
        else:
            raw_bible = await bible_update_task
            raw_summary = None

        proposed_characters_status, proposed_state, proposed_threads = parse_bible_update_response(raw_bible)
        changed = (
            proposed_characters_status != payload.current_characters_status
            or proposed_state != payload.current_runtime_state
            or proposed_threads != payload.current_runtime_threads
            or (raw_summary is not None)
        )
        return proposed_characters_status, proposed_state, proposed_threads, raw_summary, changed


class PlanningEditorService(_EditorServiceBase):
    async def generate_beats(
        self,
        session: AsyncSession,
        project_id: str,
        user_id: str,
        payload: BeatGenerateRequest,
    ) -> list[str]:
        project = await self.project_service.get_or_404(
            session, project_id, user_id=user_id,
        )
        if not project.provider:
            raise BadRequestError("项目未配置 Provider，无法调用 AI")

        style_prompt = await self._get_style_prompt(session, project, user_id)
        plot_prompt = await self._get_plot_prompt(session, project, user_id)
        generation_profile = self._require_generation_profile(
            explicit_profile=None,
            project=project,
        )

        preset_cfg = LENGTH_PRESETS.get(project.length_preset, LENGTH_PRESETS["long"])
        num_beats = payload.num_beats
        if num_beats == 8:
            num_beats = preset_cfg["beat_count_default"]

        length_context = ""
        content_length = payload.total_content_length
        if content_length > 0:
            progress = get_progress(content_length, project.length_preset)
            length_context = (
                f"【篇幅上下文】目标 {preset_cfg['target_min'] // 10000}-"
                f"{preset_cfg['target_max'] // 10000} 万字{preset_cfg['label']}，"
                f"当前进度 {content_length:,} 字 ({progress['percentage']}%)。"
            )
            if progress["phase"] == "ending_zone":
                length_context += "\n【收束提醒】已接近目标篇幅，请规划收束节拍，引导情节走向结局。"
            elif progress["phase"] == "over_target":
                length_context += "\n【超限提醒】已超出目标篇幅，请立即规划结局节拍。"

        system_prompt = build_beat_generate_system_prompt(
            style_prompt,
            plot_prompt,
            generation_profile=generation_profile,
            regenerating=bool(payload.previous_output or payload.user_feedback),
        )
        user_message = build_beat_generate_user_message(
            payload.text_before_cursor,
            payload.outline_detail,
            payload.runtime_state,
            payload.runtime_threads,
            num_beats,
            length_context=length_context,
            current_chapter_context=payload.current_chapter_context,
            previous_chapter_context=payload.previous_chapter_context,
            previous_output=payload.previous_output,
            user_feedback=payload.user_feedback,
        )

        raw = await self.llm_service.invoke_completion(
            provider_config=project.provider,
            system_prompt=system_prompt,
            user_context=user_message,
            injection_task=PromptInjectionTask.EDITOR_BEAT_GENERATION,
        )

        beats = [
            _BEAT_PREFIX_RE.sub("", line.strip())
            for line in raw.strip().splitlines()
            if line.strip()
        ]
        return [b for b in beats if b]

    async def generate_concepts(
        self,
        session: AsyncSession,
        user_id: str,
        payload: ConceptGenerateRequest,
    ) -> list[ConceptItem]:
        provider = await self.provider_config_service.ensure_enabled(
            session, payload.provider_id, user_id=user_id,
        )
        style_prompt = await self._get_style_prompt_by_id(
            session,
            payload.style_profile_id,
            user_id,
        )
        plot_prompt = await self._get_plot_prompt_by_id(
            session,
            payload.plot_profile_id,
            user_id,
        )
        generation_profile = payload.generation_profile

        regenerating = bool(payload.previous_output or payload.user_feedback)
        system_prompt = build_concept_generate_system_prompt(
            style_prompt=style_prompt,
            plot_prompt=plot_prompt,
            generation_profile=generation_profile,
            regenerating=regenerating,
        )
        user_message = build_concept_generate_user_message(
            payload.inspiration,
            payload.count,
            previous_output=payload.previous_output,
            user_feedback=payload.user_feedback,
        )

        raw = await self.llm_service.invoke_completion(
            provider_config=provider,
            system_prompt=system_prompt,
            user_context=user_message,
            model_name=payload.model,
            injection_task=PromptInjectionTask.EDITOR_CONCEPT_GENERATION,
        )

        return parse_concept_response(raw, payload.count)

    async def stream_volume_generation(
        self,
        session: AsyncSession,
        project_id: str,
        user_id: str,
        payload: VolumeGenerateRequest | None = None,
    ) -> AsyncGenerator[str, None]:
        project = await self.project_service.get_or_404(
            session, project_id, user_id=user_id,
        )
        bible = await self.project_service.get_bible_or_404(
            session, project_id, user_id=user_id,
        )
        if not project.provider:
            raise BadRequestError("项目未配置 Provider，无法调用 AI")

        style_prompt = await self._get_style_prompt(session, project, user_id)
        plot_prompt = await self._get_plot_prompt(session, project, user_id)
        generation_profile = self._require_generation_profile(
            explicit_profile=None,
            project=project,
        )

        previous_output = payload.previous_output if payload else None
        user_feedback = payload.user_feedback if payload else None
        regenerating = bool(previous_output or user_feedback)

        system_prompt = build_volume_generate_system_prompt(
            length_preset=project.length_preset,
            style_prompt=style_prompt,
            plot_prompt=plot_prompt,
            generation_profile=generation_profile,
            regenerating=regenerating,
        )
        user_message = build_volume_generate_user_message(
            bible.outline_master,
            previous_output=previous_output,
            user_feedback=user_feedback,
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        return self.llm_service.stream_messages(
            project.provider,
            messages,
            injection_task=PromptInjectionTask.EDITOR_VOLUME_GENERATION,
        )

    async def stream_volume_chapters_generation(
        self,
        session: AsyncSession,
        project_id: str,
        user_id: str,
        payload: VolumeChaptersRequest,
    ) -> AsyncGenerator[str, None]:
        project = await self.project_service.get_or_404(
            session, project_id, user_id=user_id,
        )
        bible = await self.project_service.get_bible_or_404(
            session, project_id, user_id=user_id,
        )
        if not project.provider:
            raise BadRequestError("项目未配置 Provider，无法调用 AI")

        parsed = parse_outline(bible.outline_detail or "")
        if payload.volume_index >= len(parsed["volumes"]):
            raise BadRequestError(
                f"卷索引 {payload.volume_index} 超出范围"
                f"（共 {len(parsed['volumes'])} 卷）"
            )

        target_vol = parsed["volumes"][payload.volume_index]

        preceding_parts: list[str] = []
        for i, vol in enumerate(parsed["volumes"]):
            if i >= payload.volume_index:
                break
            if vol["chapters"]:
                ch_titles = [ch["title"] for ch in vol["chapters"]]
                preceding_parts.append(
                    f"**{vol['title']}**: {', '.join(ch_titles)}"
                )
        preceding_summary = "\n".join(preceding_parts)

        style_prompt = await self._get_style_prompt(session, project, user_id)
        plot_prompt = await self._get_plot_prompt(session, project, user_id)
        generation_profile = self._require_generation_profile(
            explicit_profile=None,
            project=project,
        )

        regenerating = bool(payload.previous_output or payload.user_feedback)
        system_prompt = build_volume_chapters_system_prompt(
            style_prompt,
            plot_prompt,
            generation_profile=generation_profile,
            regenerating=regenerating,
        )
        user_message = build_volume_chapters_user_message(
            bible.outline_master,
            target_vol["title"],
            target_vol["meta"],
            preceding_summary,
            previous_output=payload.previous_output,
            user_feedback=payload.user_feedback,
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        return self.llm_service.stream_messages(
            project.provider,
            messages,
            injection_task=PromptInjectionTask.EDITOR_VOLUME_CHAPTERS_GENERATION,
        )


class EditorService:
    """Aggregate container exposing writing/memory/planning sub-services.

    Kept for DI convenience; all work is delegated to the sub-services
    which are accessed via the ``writing``/``memory``/``planning`` attributes.
    """

    def __init__(
        self,
        llm_service: LLMProviderService | None = None,
        project_service: ProjectService | None = None,
        style_profile_service: StyleProfileService | None = None,
        plot_profile_service: PlotProfileService | None = None,
        provider_config_service: ProviderConfigService | None = None,
    ) -> None:
        shared_kwargs = {
            "llm_service": llm_service,
            "project_service": project_service,
            "style_profile_service": style_profile_service,
            "plot_profile_service": plot_profile_service,
            "provider_config_service": provider_config_service,
        }
        self.writing = WritingEditorService(**shared_kwargs)
        self.memory = MemoryEditorService(**shared_kwargs)
        self.planning = PlanningEditorService(**shared_kwargs)
