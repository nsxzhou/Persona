from __future__ import annotations

import re
from typing import Any

from app.prompts.chapter_plan import (
    build_volume_chapters_system_prompt,
    build_volume_chapters_user_message,
)
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
from app.services.novel_workflow_handler_common import (
    NovelWorkflowPipelineContext,
    NovelWorkflowState,
)
from app.services.outline_parser import parse_outline


_TOP_LEVEL_HEADING_RE = re.compile(r"^#(?!#)\s+.+$")


class NovelWorkflowPlanningHandlers:
    def __init__(self, pipeline: NovelWorkflowPipelineContext) -> None:
        self.pipeline = pipeline

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
