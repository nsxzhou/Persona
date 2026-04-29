from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.prompts.active_characters import (
    build_active_characters_system_prompt,
    build_active_characters_user_message,
)
from app.prompts.continuity import (
    build_continuity_system_prompt,
    build_continuity_user_message,
    extract_continuity_verdict,
)
from app.prompts.beat import (
    build_beat_generate_system_prompt,
    build_beat_generate_user_message,
)
from app.prompts.concept import (
    build_concept_generate_system_prompt,
    build_concept_generate_user_message,
)
from app.prompts.final_editor import build_editor_polish_system_prompt
from app.prompts.memory_sync import (
    build_bible_update_system_prompt,
    build_bible_update_user_message,
    build_chapter_summary_system_prompt,
    build_chapter_summary_user_message,
    build_story_summary_system_prompt,
    build_story_summary_user_message,
    parse_bible_update_response,
)
from app.prompts.prose_writer import (
    build_beat_expand_system_prompt,
    build_beat_expand_user_message,
)

LLMComplete = Callable[..., Awaitable[str]]


class Orchestrator:
    def select_intent_node(self, intent_type: str) -> str:
        if intent_type == "chapter_write":
            return "run_chapter_write"
        if intent_type == "concept_bootstrap":
            return "run_concept_bootstrap"
        return "run_simple_intent"


@dataclass
class ActiveCharactersAgent:
    llm_complete: LLMComplete | None = None

    async def extract(
        self,
        *,
        text_before_cursor: str,
        current_chapter_context: str,
    ) -> list[str]:
        if self.llm_complete is None:
            raise RuntimeError("llm_complete is required")
        try:
            response = await self.llm_complete(
                system_prompt=build_active_characters_system_prompt(),
                user_context=build_active_characters_user_message(
                    text_before_cursor=text_before_cursor[-2000:],
                    current_chapter_context=current_chapter_context[-4000:],
                ),
                mode="analysis",
            )
        except Exception:
            return []
        return self.parse_names(response)

    @staticmethod
    def parse_names(markdown: str) -> list[str]:
        payload = _strip_json_fence(markdown)
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            return []
        if not isinstance(parsed, list):
            return []
        names: list[str] = []
        for item in parsed:
            if not isinstance(item, str):
                continue
            name = item.strip()
            if name and name not in names:
                names.append(name)
        return names


def _strip_json_fence(markdown: str) -> str:
    stripped = markdown.strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.DOTALL)
    if match:
        return match.group(1).strip()
    return stripped


@dataclass
class ConceptAgent:
    llm_complete: LLMComplete | None = None

    async def generate(
        self,
        *,
        inspiration: str,
        count: int,
        style_prompt: str | None,
        plot_prompt: str | None,
        generation_profile: Any,
        previous_output: str | None = None,
        feedback: str | None = None,
    ) -> str:
        if self.llm_complete is None:
            raise RuntimeError("llm_complete is required")
        return await self.llm_complete(
            system_prompt=build_concept_generate_system_prompt(
                style_prompt=style_prompt,
                plot_prompt=plot_prompt,
                generation_profile=generation_profile,
                regenerating=bool(previous_output or feedback),
            ),
            user_context=build_concept_generate_user_message(
                inspiration,
                count,
                previous_output=previous_output,
                user_feedback=feedback,
            ),
            mode="analysis",
        )


@dataclass
class BeatAgent:
    llm_complete: LLMComplete | None = None

    async def generate(
        self,
        *,
        state: dict[str, Any],
        current_bible: dict[str, str],
        generation_profile: Any,
        regenerating: bool = False,
    ) -> str:
        if self.llm_complete is None:
            raise RuntimeError("llm_complete is required")
        return await self.llm_complete(
            system_prompt=build_beat_generate_system_prompt(
                style_prompt=state.get("style_prompt"),
                plot_prompt=state.get("plot_prompt"),
                generation_profile=generation_profile,
                regenerating=regenerating,
            ),
            user_context=build_beat_generate_user_message(
                text_before_cursor=state.get("text_before_cursor", ""),
                outline_detail=current_bible.get("outline_detail", ""),
                runtime_state=current_bible.get("runtime_state", ""),
                runtime_threads=current_bible.get("runtime_threads", ""),
                num_beats=state.get("total_beats") or 8,
                current_chapter_context=state.get("current_chapter_context", ""),
                previous_chapter_context=state.get("previous_chapter_context", ""),
                previous_output=state.get("previous_output"),
                user_feedback=state.get("feedback"),
            ),
            mode="analysis",
        )

    async def expand(
        self,
        *,
        state: dict[str, Any],
        current_bible: dict[str, str],
        generation_profile: Any,
        beat: str,
        beat_index: int,
        total_beats: int,
        preceding_beats_prose: str,
        previous_output: str | None,
        regenerating: bool = False,
    ) -> str:
        if self.llm_complete is None:
            raise RuntimeError("llm_complete is required")
        return await self.llm_complete(
            system_prompt=build_beat_expand_system_prompt(
                style_prompt=state.get("style_prompt"),
                plot_prompt=state.get("plot_prompt"),
                generation_profile=generation_profile,
                regenerating=regenerating,
            ),
            user_context=build_beat_expand_user_message(
                text_before_cursor=state.get("text_before_cursor", ""),
                beat=beat,
                beat_index=beat_index,
                total_beats=total_beats,
                preceding_beats_prose=preceding_beats_prose,
                outline_detail=current_bible.get("outline_detail", ""),
                runtime_state=current_bible.get("runtime_state", ""),
                runtime_threads=current_bible.get("runtime_threads", ""),
                current_chapter_context=state.get("current_chapter_context", ""),
                previous_chapter_context=state.get("previous_chapter_context", ""),
                active_character_focus=current_bible.get("active_character_focus", ""),
                previous_output=previous_output,
                user_feedback=None,
            ),
            mode="immersion",
        )


@dataclass
class ContinuityAgent:
    llm_complete: LLMComplete | None = None

    async def review(
        self,
        *,
        prose_markdown: str,
        current_bible: dict[str, str],
        current_chapter_context: str,
        previous_chapter_context: str,
        beat: str | None = None,
    ) -> str:
        if self.llm_complete is None:
            raise RuntimeError("llm_complete is required")
        return await self.llm_complete(
            system_prompt=build_continuity_system_prompt(),
            user_context=build_continuity_user_message(
                prose_markdown=prose_markdown,
                current_bible=current_bible,
                current_chapter_context=current_chapter_context,
                previous_chapter_context=previous_chapter_context,
                beat=beat,
            ),
            mode="analysis",
        )

    def extract_verdict(self, markdown: str) -> str:
        return extract_continuity_verdict(markdown)


@dataclass
class EditorAgent:
    llm_complete: LLMComplete | None = None

    async def polish(self, prose_markdown: str) -> str:
        if self.llm_complete is None:
            raise RuntimeError("llm_complete is required")
        return await self.llm_complete(
            system_prompt=build_editor_polish_system_prompt(),
            user_context=prose_markdown,
            mode="analysis",
        )


@dataclass(frozen=True)
class MemorySyncResult:
    markdown: str
    characters_status: str
    runtime_state: str
    runtime_threads: str
    chapter_summary: str
    story_summary: str


@dataclass
class MemorySyncAgent:
    llm_complete: LLMComplete | None = None

    async def refresh(
        self,
        *,
        current_bible: dict[str, str],
        content_to_check: str,
        sync_scope: str = "chapter_full",
        previous_output: str | None = None,
        feedback: str | None = None,
        include_chapter_summary: bool = True,
        include_story_summary: bool = True,
    ) -> MemorySyncResult:
        if self.llm_complete is None:
            raise RuntimeError("llm_complete is required")
        memory_markdown = await self.llm_complete(
            system_prompt=build_bible_update_system_prompt(
                regenerating=bool(previous_output or feedback)
            ),
            user_context=build_bible_update_user_message(
                current_characters_status=current_bible.get("characters_status", ""),
                current_runtime_state=current_bible.get("runtime_state", ""),
                current_runtime_threads=current_bible.get("runtime_threads", ""),
                content_to_check=content_to_check,
                sync_scope=sync_scope,
                previous_output=previous_output,
                user_feedback=feedback,
            ),
            mode="analysis",
        )
        characters_status, runtime_state, runtime_threads = parse_bible_update_response(
            memory_markdown
        )
        if not characters_status.strip():
            characters_status = current_bible.get("characters_status", "")

        chapter_summary = ""
        if include_chapter_summary:
            chapter_summary = await self.llm_complete(
                system_prompt=build_chapter_summary_system_prompt(),
                user_context=build_chapter_summary_user_message(content_to_check),
                mode="analysis",
            )

        story_summary = ""
        if include_story_summary:
            story_summary = await self.llm_complete(
                system_prompt=build_story_summary_system_prompt(),
                user_context=build_story_summary_user_message(
                    current_story_summary=current_bible.get("story_summary", ""),
                    prose_markdown=content_to_check,
                ),
                mode="analysis",
            )

        return MemorySyncResult(
            markdown=memory_markdown,
            characters_status=characters_status,
            runtime_state=runtime_state,
            runtime_threads=runtime_threads,
            chapter_summary=chapter_summary,
            story_summary=story_summary,
        )
