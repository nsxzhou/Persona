"""Editor AI service — encapsulates all LLM-powered editor operations.

Streaming methods are *regular* async functions that eagerly read ORM data
(and pre-build the LLM model) while the DB session is still alive, then
return a lightweight async generator that only references plain Python
values.  This eliminates the ORM-detach risk present when an async
generator is iterated inside a ``StreamingResponse`` after the session
dependency has been torn down.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncGenerator

from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain_errors import BadRequestError, UnprocessableEntityError
from app.schemas.projects import (
    BeatExpandRequest,
    BeatGenerateRequest,
    BibleUpdateRequest,
    ConceptGenerateRequest,
    ConceptItem,
    SectionGenerateRequest,
)
from app.services.context_assembly import assemble_writing_context
from app.services.editor_prompts import (
    VALID_SECTIONS,
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
)
from app.services.llm_provider import LLMProviderService
from app.services.projects import ProjectService
from app.services.provider_configs import ProviderConfigService
from app.services.style_profiles import StyleProfileService

logger = logging.getLogger(__name__)

_BEAT_PREFIX_RE = re.compile(r"^[\d]+[.、)\]\s]+|^[-*+]\s+")


# ---- SSE response helper -------------------------------------------------- #

def sse_response(
    content_generator: AsyncGenerator[str, None],
    *,
    error_log_message: str = "SSE streaming error",
) -> StreamingResponse:
    """Wrap an async str generator into a ``text/event-stream`` response."""

    async def _sse():
        try:
            async for chunk in content_generator:
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as e:
            logger.exception(error_log_message)
            yield f"event: error\ndata: {json.dumps(str(e))}\n\n"

    return StreamingResponse(_sse(), media_type="text/event-stream")


# ---- EditorService -------------------------------------------------------- #

class EditorService:
    def __init__(
        self,
        llm_service: LLMProviderService | None = None,
        project_service: ProjectService | None = None,
        style_profile_service: StyleProfileService | None = None,
        provider_config_service: ProviderConfigService | None = None,
    ) -> None:
        self.llm_service = llm_service or LLMProviderService()
        self.project_service = project_service or ProjectService()
        self.style_profile_service = style_profile_service or StyleProfileService()
        self.provider_config_service = provider_config_service or ProviderConfigService()

    # -- private helpers ---------------------------------------------------- #

    async def _get_style_prompt(
        self,
        session: AsyncSession,
        project,
        user_id: str,
    ) -> str | None:
        """Return the style prompt_pack_payload for the project, or *None*."""
        if not project.style_profile_id:
            return None
        style_profile = await self.style_profile_service.get_or_404(
            session,
            project.style_profile_id,
            user_id=user_id,
        )
        return style_profile.prompt_pack_payload

    # -- public methods ----------------------------------------------------- #

    async def stream_completion(
        self,
        session: AsyncSession,
        project_id: str,
        user_id: str,
        text_before_cursor: str,
    ) -> AsyncGenerator[str, None]:
        project = await self.project_service.get_or_404(
            session, project_id, user_id=user_id,
        )
        if not project.style_profile_id:
            raise BadRequestError("项目未挂载风格档案")

        style_profile = await self.style_profile_service.get_or_404(
            session,
            project.style_profile_id,
            user_id=user_id,
        )
        system_prompt = assemble_writing_context(
            style_profile.prompt_pack_payload,
            inspiration=project.inspiration,
            world_building=project.world_building,
            characters=project.characters,
            outline_master=project.outline_master,
            outline_detail=project.outline_detail,
            story_bible=project.story_bible,
        )

        # Pre-build model while session is alive (reads ORM attrs + decrypts key)
        model = self.llm_service._build_model(project.provider)
        user_context = text_before_cursor

        async def _generate():
            from langchain_core.messages import HumanMessage, SystemMessage
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_context),
            ]
            async for chunk in model.astream(messages):
                if chunk.content:
                    yield chunk.content

        return _generate()

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

        system_prompt = build_section_system_prompt(payload.section, style_prompt)
        user_message = build_section_user_message(
            payload.section,
            {
                "inspiration": payload.inspiration,
                "world_building": payload.world_building,
                "characters": payload.characters,
                "outline_master": payload.outline_master,
                "outline_detail": payload.outline_detail,
                "story_bible": payload.story_bible,
            },
        )

        model = self.llm_service._build_model(project.provider)

        async def _generate():
            from langchain_core.messages import HumanMessage, SystemMessage
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message),
            ]
            async for chunk in model.astream(messages):
                if chunk.content:
                    yield chunk.content

        return _generate()

    async def propose_bible_update(
        self,
        session: AsyncSession,
        project_id: str,
        user_id: str,
        payload: BibleUpdateRequest,
    ) -> str:
        project = await self.project_service.get_or_404(
            session, project_id, user_id=user_id,
        )
        if not project.provider:
            raise BadRequestError("项目未配置 Provider，无法调用 AI")

        system_prompt = build_bible_update_system_prompt()
        user_message = build_bible_update_user_message(
            payload.current_bible,
            payload.new_content_context,
        )

        return await self.llm_service.invoke_completion(
            provider_config=project.provider,
            system_prompt=system_prompt,
            user_context=user_message,
        )

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

        system_prompt = build_beat_generate_system_prompt(style_prompt)
        user_message = build_beat_generate_user_message(
            payload.text_before_cursor,
            payload.outline_detail,
            payload.story_bible,
            payload.num_beats,
        )

        raw = await self.llm_service.invoke_completion(
            provider_config=project.provider,
            system_prompt=system_prompt,
            user_context=user_message,
        )

        beats = [
            _BEAT_PREFIX_RE.sub("", line.strip())
            for line in raw.strip().splitlines()
            if line.strip()
        ]
        return [b for b in beats if b]

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

        system_prompt = build_beat_expand_system_prompt(style_prompt)
        user_message = build_beat_expand_user_message(
            payload.text_before_cursor,
            payload.beat,
            payload.beat_index,
            payload.total_beats,
            payload.preceding_beats_prose,
            payload.outline_detail,
            payload.story_bible,
        )

        model = self.llm_service._build_model(project.provider)

        async def _generate():
            from langchain_core.messages import HumanMessage, SystemMessage
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message),
            ]
            async for chunk in model.astream(messages):
                if chunk.content:
                    yield chunk.content

        return _generate()

    async def generate_concepts(
        self,
        session: AsyncSession,
        user_id: str,
        payload: ConceptGenerateRequest,
    ) -> list[ConceptItem]:
        provider = await self.provider_config_service.ensure_enabled(
            session, payload.provider_id, user_id=user_id,
        )

        system_prompt = build_concept_generate_system_prompt()
        user_message = build_concept_generate_user_message(
            payload.inspiration, payload.count,
        )

        raw = await self.llm_service.invoke_completion(
            provider_config=provider,
            system_prompt=system_prompt,
            user_context=user_message,
            model_name=payload.model,
        )

        return self._parse_concepts(raw, payload.count)

    @staticmethod
    def _parse_concepts(raw: str, expected_count: int) -> list[ConceptItem]:
        """Parse LLM output into ConceptItem list with fault tolerance from Markdown."""
        text = raw.strip()
        concepts: list[ConceptItem] = []

        # 匹配 ### 标题，并捕获接下来的内容直到下一个 ### 或文本结束
        pattern = re.compile(r"^###\s+(.+?)\n+(.*?)(?=(?:^###|\Z))", re.MULTILINE | re.DOTALL)
        
        for match in pattern.finditer(text):
            title = match.group(1).strip()
            synopsis = match.group(2).strip()
            
            # 清理可能存在的序号，如 "1. 标题" -> "标题"
            title = re.sub(r"^\d+[\.、\s]+", "", title)
            
            if title and synopsis:
                concepts.append(ConceptItem(title=title, synopsis=synopsis))

        # Fallback 策略：如果正则没有匹配到任何内容，尝试简单的字符串分割
        if not concepts:
            parts = re.split(r'^###\s+', text, flags=re.MULTILINE)
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                lines = part.split('\n', 1)
                if len(lines) >= 2:
                    title = lines[0].strip()
                    synopsis = lines[1].strip()
                    
                    title = re.sub(r"^\d+[\.、\s]+", "", title)
                    
                    if title and synopsis:
                        concepts.append(ConceptItem(title=title, synopsis=synopsis))

        if not concepts:
            raise UnprocessableEntityError("AI 返回的格式无法解析，请重试")

        return concepts[:expected_count]
