from __future__ import annotations

import json
import re
from typing import Any

from app.prompts.chapter_plan import (
    build_volume_chapters_system_prompt,
    build_volume_chapters_user_message,
)
from app.prompts.imported_chapter_rewrite import IMPORTED_CHAPTER_FULL_REWRITE_INTENT
from app.prompts.outline import (
    build_volume_generate_system_prompt,
    build_volume_generate_user_message,
)
from app.prompts.prompt_asset_init import (
    build_prompt_asset_init_system_prompt,
    build_prompt_asset_init_user_message,
    parse_prompt_asset_init_response,
    render_prompt_asset_suggestions_markdown,
)
from app.prompts.section_router import build_section_system_prompt, build_section_user_message
from app.services.beat_parser import parse_beats_markdown
from app.services.novel_workflow_handler_common import (
    NovelWorkflowPipelineContext,
    NovelWorkflowState,
    SimpleIntentHandler,
    state_prompt_asset_layers,
    state_prompt_stack_manifest,
)
from app.services.novel_workflow_rewrite_handlers import (
    CHAPTER_REWRITE_ARTIFACT,
    CHAPTER_REWRITE_PATCHES_ARTIFACT,
    NovelWorkflowRewriteHandlers,
)
from app.services.outline_parser import parse_outline


_TOP_LEVEL_HEADING_RE = re.compile(r"^#(?!#)\s+.+$")


class NovelWorkflowSimpleIntentHandlers:
    def __init__(self, pipeline: NovelWorkflowPipelineContext) -> None:
        self.pipeline = pipeline
        self.rewrite_handlers = NovelWorkflowRewriteHandlers(pipeline)
        self.handlers: dict[str, SimpleIntentHandler] = {
            "section_generate": self.handle_section_generate,
            "volume_generate": self.handle_volume_generate,
            "volume_chapters_generate": self.handle_volume_chapters_generate,
            "selection_rewrite": self.rewrite_handlers.handle_selection_rewrite,
            "chapter_enrichment_rewrite": self.rewrite_handlers.handle_chapter_enrichment_rewrite,
            IMPORTED_CHAPTER_FULL_REWRITE_INTENT: (
                self.rewrite_handlers.handle_imported_chapter_full_rewrite
            ),
            "beats_generate": self.handle_beats_generate,
            "beat_expand": self.handle_beat_expand,
            "chapter_expand": self.handle_chapter_expand,
            "memory_refresh": self.handle_memory_refresh,
            "prompt_asset_init": self.handle_prompt_asset_init,
        }

    async def handle(
        self,
        state: NovelWorkflowState,
        current_bible: dict[str, str],
        generation_profile: Any,
    ) -> dict[str, Any]:
        handler = self.handlers.get(state["intent_type"], self.handle_concept_generate)
        return await handler(state, current_bible, generation_profile)

    async def handle_section_generate(
        self,
        state: NovelWorkflowState,
        current_bible: dict[str, str],
        generation_profile: Any,
    ) -> dict[str, Any]:
        artifact_name = "section_markdown"
        section = state.get("section") or "world_building"
        markdown = await self.pipeline._call_prompt(
            system_prompt=build_section_system_prompt(
                section,
                style_prompt=state.get("style_prompt"),
                plot_prompt=state.get("plot_prompt"),
                generation_profile=generation_profile,
                length_preset=state.get("length_preset", "long"),
                regenerating=bool(state.get("previous_output") or state.get("feedback")),
            ),
            user_context=build_section_user_message(
                section,
                {
                    "project_name": state.get("project_name", ""),
                    "description": state.get("project_description", ""),
                    "world_building": current_bible.get("world_building", ""),
                    "characters_blueprint": current_bible.get("characters_blueprint", ""),
                    "outline_master": current_bible.get("outline_master", ""),
                    "outline_detail": current_bible.get("outline_detail", ""),
                    "characters_status": current_bible.get("characters_status", ""),
                    "runtime_state": current_bible.get("runtime_state", ""),
                    "runtime_threads": current_bible.get("runtime_threads", ""),
                },
                previous_output=state.get("previous_output"),
                user_feedback=state.get("feedback"),
            ),
            mode="analysis",
        )
        if section == "outline_master":
            markdown = _normalize_outline_master_title(
                markdown,
                state.get("project_name", ""),
            )
        await self.pipeline.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name=artifact_name,
            markdown=markdown,
        )
        return {
            "latest_artifacts": [artifact_name],
            "persist_payload": {"markdown": markdown},
        }

    async def handle_volume_generate(
        self,
        state: NovelWorkflowState,
        current_bible: dict[str, str],
        generation_profile: Any,
    ) -> dict[str, Any]:
        artifact_name = "volumes_markdown"
        markdown = await self.pipeline._call_prompt(
            system_prompt=build_volume_generate_system_prompt(
                length_preset=state.get("length_preset", "long"),
                style_prompt=state.get("style_prompt"),
                plot_prompt=state.get("plot_prompt"),
                generation_profile=generation_profile,
                regenerating=bool(state.get("previous_output") or state.get("feedback")),
            ),
            user_context=build_volume_generate_user_message(
                current_bible.get("outline_master", ""),
                current_bible.get("characters_blueprint", ""),
                previous_output=state.get("previous_output"),
                user_feedback=state.get("feedback"),
            ),
            mode="analysis",
        )
        await self.pipeline.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name=artifact_name,
            markdown=markdown,
        )
        return {
            "latest_artifacts": [artifact_name],
            "persist_payload": {"markdown": markdown},
        }

    async def handle_volume_chapters_generate(
        self,
        state: NovelWorkflowState,
        current_bible: dict[str, str],
        generation_profile: Any,
    ) -> dict[str, Any]:
        artifact_name = "volume_chapters_markdown"
        volume_index = state.get("volume_index") or 0
        parsed_outline = parse_outline(current_bible.get("outline_detail", ""))
        target_volume = (
            parsed_outline["volumes"][volume_index]
            if 0 <= volume_index < len(parsed_outline["volumes"])
            else None
        )
        preceding_chapters_summary = ""
        if target_volume is not None:
            preceding_chapters = [
                chapter["raw_markdown"]
                for volume in parsed_outline["volumes"][:volume_index]
                for chapter in volume["chapters"]
            ]
            preceding_chapters_summary = "\n\n".join(preceding_chapters[-12:])

        markdown = await self.pipeline._call_prompt(
            system_prompt=build_volume_chapters_system_prompt(
                length_preset=state.get("length_preset", "long"),
                style_prompt=state.get("style_prompt"),
                plot_prompt=state.get("plot_prompt"),
                generation_profile=generation_profile,
                regenerating=bool(state.get("previous_output") or state.get("feedback")),
            ),
            user_context=build_volume_chapters_user_message(
                current_bible.get("outline_master", ""),
                current_bible.get("characters_blueprint", ""),
                target_volume["title"] if target_volume is not None else f"第{volume_index + 1}卷",
                target_volume["meta"] if target_volume is not None else "",
                preceding_chapters_summary,
                target_volume["body_markdown"] if target_volume is not None else "",
                previous_output=state.get("previous_output"),
                user_feedback=state.get("feedback"),
            ),
            mode="analysis",
        )
        await self.pipeline.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name=artifact_name,
            markdown=markdown,
        )
        return {
            "latest_artifacts": [artifact_name],
            "persist_payload": {"markdown": markdown},
        }

    async def handle_beats_generate(
        self,
        state: NovelWorkflowState,
        current_bible: dict[str, str],
        generation_profile: Any,
    ) -> dict[str, Any]:
        artifact_name = "beats_markdown"
        markdown = await self.pipeline.beat_agent.generate(
            state=state,
            current_bible=current_bible,
            generation_profile=generation_profile,
            regenerating=bool(state.get("previous_output") or state.get("feedback")),
        )
        await self.pipeline.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name=artifact_name,
            markdown=markdown,
        )
        return {
            "latest_artifacts": [artifact_name],
            "persist_payload": {"markdown": markdown},
        }

    async def handle_beat_expand(
        self,
        state: NovelWorkflowState,
        current_bible: dict[str, str],
        generation_profile: Any,
    ) -> dict[str, Any]:
        artifact_name = "prose_markdown"
        focused_bible = (
            await self.pipeline._select_writing_context(state, current_bible)
        ).as_bible()
        markdown = await self.pipeline.beat_agent.expand(
            state=state,
            current_bible=focused_bible,
            generation_profile=generation_profile,
            beat=state.get("beat") or "",
            beat_index=state.get("beat_index") or 0,
            total_beats=state.get("total_beats") or 1,
            preceding_beats_prose=state.get("preceding_beats_prose", ""),
            previous_output=state.get("previous_output"),
            regenerating=bool(state.get("previous_output") or state.get("feedback")),
            prompt_stack_manifest=state_prompt_stack_manifest(state),
            prompt_asset_layers=state_prompt_asset_layers(state),
        )
        await self.pipeline.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name=artifact_name,
            markdown=markdown,
        )
        return {
            "latest_artifacts": [artifact_name],
            "persist_payload": {"markdown": markdown},
        }

    async def handle_chapter_expand(
        self,
        state: NovelWorkflowState,
        current_bible: dict[str, str],
        generation_profile: Any,
    ) -> dict[str, Any]:
        artifact_name = "prose_markdown"
        focused_bible = (
            await self.pipeline._select_writing_context(state, current_bible)
        ).as_bible()
        beats = [beat.strip() for beat in state.get("beats", []) if beat.strip()]
        if not beats:
            beats = parse_beats_markdown(state.get("beats_markdown", ""))
        markdown = await self.pipeline.beat_agent.expand_chapter(
            state=state,
            current_bible=focused_bible,
            generation_profile=generation_profile,
            beats=beats,
            previous_output=state.get("previous_output"),
            user_feedback=state.get("feedback"),
            regenerating=bool(state.get("previous_output") or state.get("feedback")),
            prompt_stack_manifest=state_prompt_stack_manifest(state),
            prompt_asset_layers=state_prompt_asset_layers(state),
        )
        try:
            review_raw = await self.pipeline.beat_agent.review_chapter_expansion(
                beats=beats,
                prose_markdown=markdown,
            )
        except Exception:
            review_raw = json.dumps(
                {"issues": ["章节审校未完成：审校调用失败，已保留生成正文"]},
                ensure_ascii=False,
            )
        review_issues = _parse_chapter_expand_review_issues(review_raw)
        await self.pipeline.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name=artifact_name,
            markdown=markdown,
        )
        await self.pipeline.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name="chapter_expand_review",
            markdown=review_raw,
        )
        warnings = list(state.get("warnings", []))
        warnings.extend(review_issues)
        return {
            "latest_artifacts": [artifact_name, "chapter_expand_review"],
            "warnings": warnings,
            "persist_payload": {
                "markdown": markdown,
                "review_issues": review_issues,
            },
        }

    async def handle_memory_refresh(
        self,
        state: NovelWorkflowState,
        current_bible: dict[str, str],
        _generation_profile: Any,
    ) -> dict[str, Any]:
        artifact_name = "memory_update_bundle"
        memory_result = await self.pipeline.memory_sync_agent.refresh(
            current_bible=current_bible,
            content_to_check=state.get("content_to_check", ""),
            sync_scope=state.get("sync_scope") or "chapter_full",
            previous_output=state.get("previous_output"),
            feedback=state.get("feedback"),
            include_chapter_summary=(state.get("sync_scope") or "chapter_full")
            == "chapter_full",
            include_story_summary=False,
        )
        markdown = memory_result.markdown
        await self.pipeline.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name=artifact_name,
            markdown=markdown,
        )
        latest_artifacts = [artifact_name]
        if memory_result.chapter_summary:
            await self.pipeline.storage_service.write_stage_markdown_artifact(
                state["run_id"],
                name="chapter_summary_markdown",
                markdown=memory_result.chapter_summary,
            )
            latest_artifacts.append("chapter_summary_markdown")
        return {
            "latest_artifacts": latest_artifacts,
            "persist_payload": {
                "markdown": markdown,
                "chapter_summary": memory_result.chapter_summary,
            },
        }

    async def handle_prompt_asset_init(
        self,
        state: NovelWorkflowState,
        current_bible: dict[str, str],
        _generation_profile: Any,
    ) -> dict[str, Any]:
        artifact_name = "prompt_asset_suggestions"
        raw = await self.pipeline._call_prompt(
            system_prompt=build_prompt_asset_init_system_prompt(),
            user_context=build_prompt_asset_init_user_message(
                project_name=state.get("project_name", ""),
                project_description=state.get("project_description", ""),
                current_bible=current_bible,
                existing_assets=state.get("prompt_assets", []),
            ),
            mode="none",
        )
        suggestions = parse_prompt_asset_init_response(raw)
        markdown = render_prompt_asset_suggestions_markdown(suggestions)
        await self.pipeline.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name=artifact_name,
            markdown=markdown,
        )
        return {
            "latest_artifacts": [artifact_name],
            "persist_payload": {"markdown": markdown},
        }

    async def handle_concept_generate(
        self,
        state: NovelWorkflowState,
        _current_bible: dict[str, str],
        generation_profile: Any,
    ) -> dict[str, Any]:
        artifact_name = "concepts_markdown"
        markdown = await self.pipeline.concept_agent.generate(
            inspiration=state.get("inspiration", ""),
            count=state.get("count") or 3,
            style_prompt=state.get("style_prompt"),
            plot_prompt=state.get("plot_prompt"),
            generation_profile=generation_profile,
            previous_output=state.get("previous_output"),
            feedback=state.get("feedback"),
        )
        await self.pipeline.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name=artifact_name,
            markdown=markdown,
        )
        return {
            "latest_artifacts": [artifact_name],
            "persist_payload": {"markdown": markdown},
        }

def _format_project_book_title(project_name: str | None) -> str:
    stripped = (project_name or "").strip()
    if not stripped:
        return ""
    if stripped.startswith("《") and stripped.endswith("》"):
        return stripped
    return f"《{stripped.strip('《》')}》"


def _normalize_outline_master_title(markdown: str, project_name: str | None) -> str:
    book_title = _format_project_book_title(project_name)
    if not book_title:
        return markdown

    expected_heading = f"# {book_title} 全书总纲"
    stripped = markdown.strip()
    if not stripped:
        return expected_heading

    lines = stripped.splitlines()
    if lines and _TOP_LEVEL_HEADING_RE.match(lines[0]):
        lines[0] = expected_heading
        return "\n".join(lines).strip()
    return f"{expected_heading}\n\n{stripped}"


_state_prompt_stack_manifest = state_prompt_stack_manifest
_state_prompt_asset_layers = state_prompt_asset_layers


def _parse_chapter_expand_review_issues(markdown: str) -> list[str]:
    stripped = markdown.strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.DOTALL)
    if match:
        stripped = match.group(1).strip()
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return [stripped] if stripped else []
    issues = payload.get("issues") if isinstance(payload, dict) else payload
    if not isinstance(issues, list):
        return [stripped] if stripped else []
    return [issue.strip() for issue in issues if isinstance(issue, str) and issue.strip()]
