from __future__ import annotations

from typing import Any

from app.services.beat_parser import parse_beats_markdown
from app.services.novel_workflow_simple_handlers import (
    _state_prompt_asset_layers,
    _state_prompt_stack_manifest,
)
from app.services.prose_validation import validate_limited_third_prose


class NovelWorkflowChapterWriteOrchestrator:
    def __init__(self, pipeline: Any) -> None:
        self.pipeline = pipeline

    async def finalize(self, state: dict[str, Any]) -> dict[str, Any]:
        prose_markdown, warnings = await self.write_from_beats(state)
        if validate_limited_third_prose(prose_markdown):
            warnings.append("limited_third_pov_retry")
            prose_markdown, retry_warnings = await self.write_from_beats(
                {
                    **state,
                    "previous_output": prose_markdown,
                    "feedback": "请严格保持限制性第三人称视角，不要使用括号式内心独白或第一人称内心句式。",
                }
            )
            warnings.extend(retry_warnings)
            if validate_limited_third_prose(prose_markdown):
                raise ValueError("限制性第三人称视角校验失败")
        return {
            "prose_markdown": prose_markdown,
            "warnings": warnings,
            "persist_payload": {
                "chapter": {
                    "content": prose_markdown,
                    "beats_markdown": state.get("beats_markdown", ""),
                },
                "markdown": prose_markdown,
            },
        }

    async def write_from_beats(self, state: dict[str, Any]) -> tuple[str, list[str]]:
        current_bible = state.get("current_bible", {})
        selected_context = await self.pipeline._select_writing_context(state, current_bible)
        focused_bible = selected_context.as_bible()
        beats = parse_beats_markdown(state.get("beats_markdown", ""))
        warnings = list(state.get("warnings", []))
        prose_parts: list[str] = []

        for index, beat in enumerate(beats):
            accepted = ""
            for attempt in range(3):
                prose_candidate = await self.pipeline.beat_agent.expand(
                    state=state,
                    current_bible=focused_bible,
                    generation_profile=self.pipeline._generation_profile_obj(state),
                    beat=beat,
                    beat_index=index,
                    total_beats=len(beats),
                    preceding_beats_prose="".join(prose_parts),
                    previous_output=accepted or None,
                    user_feedback=state.get("feedback"),
                    regenerating=attempt > 0,
                    prompt_stack_manifest=_state_prompt_stack_manifest(state),
                    prompt_asset_layers=_state_prompt_asset_layers(state),
                )
                continuity = await self.pipeline.continuity_agent.review(
                    prose_markdown=prose_candidate,
                    current_bible=focused_bible,
                    current_chapter_context=state.get("current_chapter_context", ""),
                    previous_chapter_context=state.get("previous_chapter_context", ""),
                    beat=beat,
                )
                verdict = self.pipeline.continuity_agent.extract_verdict(continuity)
                if verdict == "pass":
                    accepted = prose_candidate
                    break
                if attempt == 2:
                    warnings.append(f"beat_{index}_continuity_warning")
                    accepted = prose_candidate
            prose_parts.append(accepted)

        return "".join(prose_parts), warnings
