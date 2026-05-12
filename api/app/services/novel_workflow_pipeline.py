from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, NotRequired, TypedDict

from langgraph.checkpoint.memory import InMemorySaver

from app.prompts.imported_chapter_rewrite import state_chapter_title
from app.schemas.novel_workflows import (
    NOVEL_WORKFLOW_STAGE_GENERATING,
    NOVEL_WORKFLOW_STAGE_PERSISTING,
    NOVEL_WORKFLOW_STAGE_PREPARING,
    NOVEL_WORKFLOW_STAGE_WAITING_DECISION,
)
from app.services.prompt_stack import PromptStackSelection
from app.services.novel_workflow_agents import (
    ActiveCharactersAgent,
    BeatAgent,
    ConceptAgent,
    ContinuityAgent,
    EditorAgent,
    MemorySyncAgent,
    Orchestrator,
)
from app.services.novel_workflow_simple_handlers import (
    NovelWorkflowSimpleIntentHandlers,
)
from app.services.novel_workflow_chapter_writer import NovelWorkflowChapterWriteOrchestrator
from app.services.novel_workflow_graph import build_novel_workflow_graph
from app.services.novel_workflow_storage import NovelWorkflowStorageService
from app.services.writing_context_selection import (
    SelectedWritingContext,
    select_writing_context,
)


LLMComplete = Callable[..., Awaitable[str]]
DecisionLoader = Callable[[str], dict[str, Any] | None]
StageCallback = Callable[[str | None], Awaitable[None]]

_IMPORTED_ACTIVE_CHARACTER_SAMPLE_CHARS = 2_000


class NovelWorkflowAwaitingHuman(Exception):
    def __init__(self, checkpoint_kind: str) -> None:
        super().__init__(checkpoint_kind)
        self.checkpoint_kind = checkpoint_kind


class NovelWorkflowState(TypedDict):
    run_id: str
    intent_type: str
    project_id: NotRequired[str | None]
    chapter_id: NotRequired[str | None]
    project_name: NotRequired[str]
    project_description: NotRequired[str]
    length_preset: NotRequired[str]
    style_prompt: NotRequired[str]
    plot_prompt: NotRequired[str]
    generation_profile: NotRequired[dict[str, Any] | None]
    current_bible: NotRequired[dict[str, str]]
    chapter_snapshot: NotRequired[dict[str, str]]
    text_before_cursor: NotRequired[str]
    selected_text: NotRequired[str]
    text_before_selection: NotRequired[str]
    text_after_selection: NotRequired[str]
    rewrite_instruction: NotRequired[str]
    current_chapter_context: NotRequired[str]
    previous_chapter_context: NotRequired[str]
    imported_previous_chapter: NotRequired[dict[str, str] | None]
    imported_next_chapter: NotRequired[dict[str, str] | None]
    total_content_length: NotRequired[int]
    volume_index: NotRequired[int | None]
    section: NotRequired[str | None]
    inspiration: NotRequired[str]
    count: NotRequired[int | None]
    content_to_check: NotRequired[str]
    sync_scope: NotRequired[str | None]
    feedback: NotRequired[str | None]
    previous_output: NotRequired[str | None]
    beat: NotRequired[str | None]
    beats: NotRequired[list[str]]
    beat_index: NotRequired[int | None]
    total_beats: NotRequired[int | None]
    preceding_beats_prose: NotRequired[str]
    enable_editor_pass: NotRequired[bool]
    expansion_ratio_percent: NotRequired[int]
    chapter_rewrite_retry_invalid_output: NotRequired[str | None]
    chapter_rewrite_retry_validation_error: NotRequired[str | None]

    outline_master: NotRequired[str]
    world_building: NotRequired[str]
    characters_blueprint: NotRequired[str]
    outline_detail: NotRequired[str]
    characters_status: NotRequired[str]
    runtime_state: NotRequired[str]
    runtime_threads: NotRequired[str]
    story_summary: NotRequired[str]
    prompt_assets: NotRequired[list[Any]]
    beats_markdown: NotRequired[str]
    prose_markdown: NotRequired[str]
    continuity_report_markdown: NotRequired[str]
    latest_artifacts: NotRequired[list[str]]
    warnings: NotRequired[list[str]]
    checkpoint_kind: NotRequired[str | None]
    persist_payload: NotRequired[dict[str, Any]]
    prompt_stack: NotRequired[PromptStackSelection | None]


@dataclass(frozen=True)
class NovelWorkflowPipelineResult:
    persist_payload: dict[str, Any]
    latest_artifacts: list[str]
    warnings: list[str] = field(default_factory=list)
    checkpoint_kind: str | None = None


@dataclass(frozen=True)
class ImportedRewriteCharacterContext:
    active_character_focus: str
    active_character_names: list[str]


class NovelWorkflowPipeline:
    def __init__(
        self,
        *,
        llm_complete: LLMComplete,
        storage_service: NovelWorkflowStorageService | None = None,
        checkpointer: Any | None = None,
        decision_loader: DecisionLoader | None = None,
        stage_callback: StageCallback | None = None,
        should_pause: Callable[[], bool] | None = None,
    ) -> None:
        self.llm_complete = llm_complete
        self.storage_service = storage_service or NovelWorkflowStorageService()
        self.checkpointer = checkpointer or InMemorySaver()
        self.decision_loader = decision_loader or (lambda _run_id: None)
        self.stage_callback = stage_callback
        self.should_pause = should_pause
        agent_llm = self._call_prompt
        self.orchestrator = Orchestrator()
        self.active_characters_agent = ActiveCharactersAgent(agent_llm)
        self.concept_agent = ConceptAgent(agent_llm)
        self.beat_agent = BeatAgent(agent_llm)
        self.continuity_agent = ContinuityAgent(agent_llm)
        self.editor_agent = EditorAgent(agent_llm)
        self.memory_sync_agent = MemorySyncAgent(agent_llm)
        self.simple_intent_handlers = NovelWorkflowSimpleIntentHandlers(self)
        self.chapter_write_orchestrator = NovelWorkflowChapterWriteOrchestrator(self)
        self.graph = build_novel_workflow_graph(
            state_type=NovelWorkflowState,
            pipeline=self,
            checkpointer=self.checkpointer,
        )

    async def run(
        self,
        *,
        run_id: str,
        initial_state: dict[str, Any],
    ) -> NovelWorkflowPipelineResult:
        graph_input: NovelWorkflowState = {"run_id": run_id, **initial_state}
        config = {"configurable": {"thread_id": run_id}}
        checkpoint_state = await self.graph.aget_state(config)
        invoke_input = None if checkpoint_state.next else graph_input
        final_state = await self.graph.ainvoke(invoke_input, config)
        await self._set_stage(None)
        return NovelWorkflowPipelineResult(
            persist_payload=final_state.get("persist_payload", {}),
            latest_artifacts=final_state.get("latest_artifacts", []),
            warnings=final_state.get("warnings", []),
            checkpoint_kind=final_state.get("checkpoint_kind"),
        )

    async def _prepare_input(self, state: NovelWorkflowState) -> dict[str, Any]:
        await self._set_stage(NOVEL_WORKFLOW_STAGE_PREPARING)
        await self.storage_service.append_job_log(
            state["run_id"],
            f"[Workflow] 准备执行 {state['intent_type']}",
        )
        return {"latest_artifacts": [], "warnings": []}

    async def _route_intent(self, _state: NovelWorkflowState) -> dict[str, Any]:
        return {}

    def _select_intent_node(self, state: NovelWorkflowState) -> str:
        return self.orchestrator.select_intent_node(state["intent_type"])

    async def _run_chapter_write(self, state: NovelWorkflowState) -> dict[str, Any]:
        await self._set_stage(NOVEL_WORKFLOW_STAGE_GENERATING)
        current_bible = state.get("current_bible", {})
        markdown = await self.beat_agent.generate(
            state=state,
            current_bible=current_bible,
            generation_profile=self._generation_profile_obj(state),
            regenerating=bool(state.get("previous_output") or state.get("feedback")),
        )
        await self.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name="beats_markdown",
            markdown=markdown,
        )
        return {
            "beats_markdown": markdown,
            "checkpoint_kind": "beats",
            "latest_artifacts": ["beats_markdown"],
        }

    async def _review_beats(self, state: NovelWorkflowState) -> dict[str, Any]:
        await self._set_stage(NOVEL_WORKFLOW_STAGE_WAITING_DECISION)
        decision = self.decision_loader(state["run_id"])
        if not decision or decision.get("artifact_name") != "beats_markdown":
            raise NovelWorkflowAwaitingHuman("beats")

        if decision.get("action") == "revise" and decision.get("edited_markdown"):
            return {
                "beats_markdown": decision["edited_markdown"],
                "checkpoint_kind": None,
            }
        return {"checkpoint_kind": None}

    async def _finalize_chapter_write(self, state: NovelWorkflowState) -> dict[str, Any]:
        await self._set_stage(NOVEL_WORKFLOW_STAGE_GENERATING)
        result = await self.chapter_write_orchestrator.finalize(state)
        prose_markdown = result["prose_markdown"]
        await self.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name="prose_markdown",
            markdown=prose_markdown,
        )
        await self._set_stage(NOVEL_WORKFLOW_STAGE_PERSISTING)
        return {
            "latest_artifacts": ["beats_markdown", "prose_markdown"],
            "warnings": result["warnings"],
            "persist_payload": result["persist_payload"],
        }

    async def _run_concept_bootstrap(self, state: NovelWorkflowState) -> dict[str, Any]:
        await self._set_stage(NOVEL_WORKFLOW_STAGE_GENERATING)
        markdown = await self.concept_agent.generate(
            inspiration=state.get("inspiration", ""),
            count=state.get("count") or 3,
            style_prompt=state.get("style_prompt"),
            plot_prompt=state.get("plot_prompt"),
            generation_profile=self._generation_profile_obj(state),
            previous_output=state.get("previous_output"),
            feedback=state.get("feedback"),
        )
        await self.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name="concepts_markdown",
            markdown=markdown,
        )
        return {
            "latest_artifacts": ["concepts_markdown"],
            "persist_payload": {"markdown": markdown},
        }

    async def _run_simple_intent(self, state: NovelWorkflowState) -> dict[str, Any]:
        await self._set_stage(NOVEL_WORKFLOW_STAGE_GENERATING)
        current_bible = state.get("current_bible", {})
        generation_profile = self._generation_profile_obj(state)
        return await self.simple_intent_handlers.handle(
            state,
            current_bible,
            generation_profile,
        )

    async def _handle_beat_expand(
        self,
        state: NovelWorkflowState,
        current_bible: dict[str, str],
        generation_profile: Any,
    ) -> dict[str, Any]:
        return await self.simple_intent_handlers.handle_beat_expand(
            state,
            current_bible,
            generation_profile,
        )

    async def _write_chapter_from_beats(
        self,
        state: NovelWorkflowState,
    ) -> tuple[str, list[str]]:
        return await self.chapter_write_orchestrator.write_from_beats(state)

    async def _select_writing_context(
        self,
        state: NovelWorkflowState,
        current_bible: dict[str, str],
    ) -> SelectedWritingContext:
        active_character_names = await self.active_characters_agent.extract(
            text_before_cursor=state.get("text_before_cursor", ""),
            current_chapter_context=state.get("current_chapter_context", ""),
        )
        return select_writing_context(
            current_bible=current_bible,
            active_character_names=active_character_names,
            current_chapter_context=state.get("current_chapter_context", ""),
            text_before_cursor=state.get("text_before_cursor", ""),
            description=state.get("project_description", ""),
        )

    async def _select_imported_rewrite_character_context(
        self,
        state: NovelWorkflowState,
        current_bible: dict[str, str],
        chapter_content: str,
    ) -> "ImportedRewriteCharacterContext":
        sample = _sample_head_middle_tail(
            chapter_content,
            segment_chars=_IMPORTED_ACTIVE_CHARACTER_SAMPLE_CHARS,
        )
        active_character_names = await self.active_characters_agent.extract(
            text_before_cursor=sample,
            current_chapter_context=state_chapter_title(state),
            preserve_text_sample=True,
        )
        if not active_character_names:
            return ImportedRewriteCharacterContext(
                active_character_focus="",
                active_character_names=[],
            )
        selected_context = select_writing_context(
            current_bible=current_bible,
            active_character_names=active_character_names,
            current_chapter_context=state_chapter_title(state),
            text_before_cursor=sample,
            description="",
        )
        return ImportedRewriteCharacterContext(
            active_character_focus=selected_context.active_character_focus,
            active_character_names=active_character_names,
        )

    async def _call_prompt(
        self,
        *,
        system_prompt: str,
        user_context: str,
        mode: str,
        prompt_stack_manifest: dict | None = None,
    ) -> str:
        if self.should_pause is not None and self.should_pause():
            raise NovelWorkflowAwaitingHuman("manual_pause")
        kwargs = {
            "system_prompt": system_prompt,
            "user_context": user_context,
            "mode": mode,
        }
        if prompt_stack_manifest is not None:
            kwargs["prompt_stack_manifest"] = prompt_stack_manifest
        content = await self.llm_complete(**kwargs)
        return re.sub(r"<think>.*?(?:</think>\n*|\Z)", "", content, flags=re.DOTALL).strip()

    async def _set_stage(self, stage: str | None) -> None:
        if self.stage_callback is not None:
            await self.stage_callback(stage)

    def _generation_profile_obj(self, state: NovelWorkflowState):
        from app.schemas.prompt_profiles import default_generation_profile, validate_generation_profile

        payload = state.get("generation_profile")
        if payload:
            return validate_generation_profile(payload)
        return default_generation_profile()


def _sample_head_middle_tail(text: str, *, segment_chars: int) -> str:
    stripped = text.strip()
    if len(stripped) <= segment_chars * 3:
        return stripped
    middle_start = max((len(stripped) - segment_chars) // 2, segment_chars)
    return "\n\n".join(
        (
            stripped[:segment_chars],
            stripped[middle_start : middle_start + segment_chars],
            stripped[-segment_chars:],
        )
    )
