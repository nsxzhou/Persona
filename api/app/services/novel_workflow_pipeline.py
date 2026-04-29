from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, NotRequired, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.prompts.chapter_plan import (
    build_volume_chapters_system_prompt,
    build_volume_chapters_user_message,
)
from app.prompts.outline import (
    build_volume_generate_system_prompt,
    build_volume_generate_user_message,
)
from app.prompts.section_router import build_section_system_prompt, build_section_user_message
from app.schemas.novel_workflows import (
    NOVEL_WORKFLOW_STAGE_GENERATING,
    NOVEL_WORKFLOW_STAGE_PERSISTING,
    NOVEL_WORKFLOW_STAGE_PREPARING,
    NOVEL_WORKFLOW_STAGE_WAITING_DECISION,
)
from app.schemas.prompt_profiles import build_chapter_objective_card, build_intensity_profile
from app.services.context_assembly import WritingContextSections, assemble_writing_context
from app.services.novel_workflow_agents import (
    ActiveCharactersAgent,
    BeatAgent,
    ConceptAgent,
    ContinuityAgent,
    EditorAgent,
    MemorySyncAgent,
    Orchestrator,
)
from app.services.novel_workflow_storage import NovelWorkflowStorageService
from app.services.writing_context_selection import (
    SelectedWritingContext,
    select_writing_context,
)


LLMComplete = Callable[..., Awaitable[str]]
DecisionLoader = Callable[[str], dict[str, Any] | None]
StageCallback = Callable[[str | None], Awaitable[None]]

_BEAT_LINE_RE = re.compile(r"^\s*[-*+]?\s*")


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
    beat_index: NotRequired[int | None]
    total_beats: NotRequired[int | None]
    preceding_beats_prose: NotRequired[str]
    enable_editor_pass: NotRequired[bool]

    outline_master: NotRequired[str]
    world_building: NotRequired[str]
    characters_blueprint: NotRequired[str]
    outline_detail: NotRequired[str]
    characters_status: NotRequired[str]
    runtime_state: NotRequired[str]
    runtime_threads: NotRequired[str]
    story_summary: NotRequired[str]
    beats_markdown: NotRequired[str]
    prose_markdown: NotRequired[str]
    continuity_report_markdown: NotRequired[str]
    latest_artifacts: NotRequired[list[str]]
    warnings: NotRequired[list[str]]
    checkpoint_kind: NotRequired[str | None]
    persist_payload: NotRequired[dict[str, Any]]


@dataclass(frozen=True)
class NovelWorkflowPipelineResult:
    persist_payload: dict[str, Any]
    latest_artifacts: list[str]
    warnings: list[str] = field(default_factory=list)
    checkpoint_kind: str | None = None


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
        self._simple_intent_handlers = {
            "section_generate": self._handle_section_generate,
            "volume_generate": self._handle_volume_generate,
            "volume_chapters_generate": self._handle_volume_chapters_generate,
            "selection_rewrite": self._handle_selection_rewrite,
            "beats_generate": self._handle_beats_generate,
            "beat_expand": self._handle_beat_expand,
            "memory_refresh": self._handle_memory_refresh,
        }
        self.graph = self._build_graph()

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

    def _build_graph(self):
        builder = StateGraph(NovelWorkflowState)
        builder.add_node("prepare_input", self._prepare_input)
        builder.add_node("route_intent", self._route_intent)
        builder.add_node("run_chapter_write", self._run_chapter_write)
        builder.add_node("review_beats", self._review_beats)
        builder.add_node("finalize_chapter_write", self._finalize_chapter_write)
        builder.add_node("run_concept_bootstrap", self._run_concept_bootstrap)
        builder.add_node("run_simple_intent", self._run_simple_intent)

        builder.add_edge(START, "prepare_input")
        builder.add_edge("prepare_input", "route_intent")
        builder.add_conditional_edges(
            "route_intent",
            self._select_intent_node,
            [
                "run_chapter_write",
                "run_concept_bootstrap",
                "run_simple_intent",
            ],
        )

        builder.add_edge("run_chapter_write", "review_beats")
        builder.add_edge("review_beats", "finalize_chapter_write")
        builder.add_edge("finalize_chapter_write", END)

        builder.add_edge("run_concept_bootstrap", END)
        builder.add_edge("run_simple_intent", END)
        return builder.compile(checkpointer=self.checkpointer)

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
        prose_markdown, warnings = await self._write_chapter_from_beats(state)
        await self.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name="prose_markdown",
            markdown=prose_markdown,
        )
        await self._set_stage(NOVEL_WORKFLOW_STAGE_PERSISTING)
        return {
            "latest_artifacts": ["beats_markdown", "prose_markdown"],
            "warnings": warnings,
            "persist_payload": {
                "chapter": {
                    "content": prose_markdown,
                    "beats_markdown": state.get("beats_markdown", ""),
                },
                "markdown": prose_markdown,
            },
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
        intent = state["intent_type"]
        current_bible = state.get("current_bible", {})
        generation_profile = self._generation_profile_obj(state)

        handler = self._simple_intent_handlers.get(intent, self._handle_concept_generate)
        return await handler(state, current_bible, generation_profile)

    async def _handle_section_generate(self, state: NovelWorkflowState, current_bible: dict[str, str], generation_profile: Any) -> dict[str, Any]:
        artifact_name = "section_markdown"
        section = state.get("section") or "world_building"
        markdown = await self._call_prompt(
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
        await self.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name=artifact_name,
            markdown=markdown,
        )
        return {
            "latest_artifacts": [artifact_name],
            "persist_payload": {"markdown": markdown},
        }

    async def _handle_volume_generate(self, state: NovelWorkflowState, current_bible: dict[str, str], generation_profile: Any) -> dict[str, Any]:
        artifact_name = "volumes_markdown"
        markdown = await self._call_prompt(
            system_prompt=build_volume_generate_system_prompt(
                length_preset=state.get("length_preset", "long"),
                style_prompt=state.get("style_prompt"),
                plot_prompt=state.get("plot_prompt"),
                generation_profile=generation_profile,
                regenerating=bool(state.get("previous_output") or state.get("feedback")),
            ),
            user_context=build_volume_generate_user_message(
                current_bible.get("outline_master", ""),
                previous_output=state.get("previous_output"),
                user_feedback=state.get("feedback"),
            ),
            mode="analysis",
        )
        await self.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name=artifact_name,
            markdown=markdown,
        )
        return {
            "latest_artifacts": [artifact_name],
            "persist_payload": {"markdown": markdown},
        }

    async def _handle_volume_chapters_generate(self, state: NovelWorkflowState, current_bible: dict[str, str], generation_profile: Any) -> dict[str, Any]:
        artifact_name = "volume_chapters_markdown"
        markdown = await self._call_prompt(
            system_prompt=build_volume_chapters_system_prompt(
                length_preset=state.get("length_preset", "long"),
                style_prompt=state.get("style_prompt"),
                plot_prompt=state.get("plot_prompt"),
                generation_profile=generation_profile,
                regenerating=bool(state.get("previous_output") or state.get("feedback")),
            ),
            user_context=build_volume_chapters_user_message(
                current_bible.get("outline_master", ""),
                f"第{(state.get('volume_index') or 0) + 1}卷",
                "",
                "",
                previous_output=state.get("previous_output"),
                user_feedback=state.get("feedback"),
            ),
            mode="analysis",
        )
        await self.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name=artifact_name,
            markdown=markdown,
        )
        return {
            "latest_artifacts": [artifact_name],
            "persist_payload": {"markdown": markdown},
        }

    async def _handle_selection_rewrite(self, state: NovelWorkflowState, current_bible: dict[str, str], generation_profile: Any) -> dict[str, Any]:
        artifact_name = "prose_markdown"
        markdown = await self._generate_selection_rewrite(state)
        await self.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name=artifact_name,
            markdown=markdown,
        )
        return {
            "latest_artifacts": [artifact_name],
            "persist_payload": {"markdown": markdown},
        }

    async def _handle_beats_generate(self, state: NovelWorkflowState, current_bible: dict[str, str], generation_profile: Any) -> dict[str, Any]:
        artifact_name = "beats_markdown"
        markdown = await self.beat_agent.generate(
            state=state,
            current_bible=current_bible,
            generation_profile=generation_profile,
            regenerating=bool(state.get("previous_output") or state.get("feedback")),
        )
        await self.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name=artifact_name,
            markdown=markdown,
        )
        return {
            "latest_artifacts": [artifact_name],
            "persist_payload": {"markdown": markdown},
        }

    async def _handle_beat_expand(self, state: NovelWorkflowState, current_bible: dict[str, str], generation_profile: Any) -> dict[str, Any]:
        artifact_name = "prose_markdown"
        focused_bible = (
            await self._select_writing_context(state, current_bible)
        ).as_bible()
        markdown = await self.beat_agent.expand(
            state=state,
            current_bible=focused_bible,
            generation_profile=generation_profile,
            beat=state.get("beat") or "",
            beat_index=state.get("beat_index") or 0,
            total_beats=state.get("total_beats") or 1,
            preceding_beats_prose=state.get("preceding_beats_prose", ""),
            previous_output=state.get("previous_output"),
            regenerating=bool(state.get("previous_output") or state.get("feedback")),
        )
        await self.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name=artifact_name,
            markdown=markdown,
        )
        return {
            "latest_artifacts": [artifact_name],
            "persist_payload": {"markdown": markdown},
        }

    async def _handle_memory_refresh(self, state: NovelWorkflowState, current_bible: dict[str, str], generation_profile: Any) -> dict[str, Any]:
        artifact_name = "memory_update_bundle"
        memory_result = await self.memory_sync_agent.refresh(
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
        await self.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name=artifact_name,
            markdown=markdown,
        )
        latest_artifacts = [artifact_name]
        if memory_result.chapter_summary:
            await self.storage_service.write_stage_markdown_artifact(
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

    async def _handle_concept_generate(self, state: NovelWorkflowState, current_bible: dict[str, str], generation_profile: Any) -> dict[str, Any]:
        artifact_name = "concepts_markdown"
        markdown = await self.concept_agent.generate(
            inspiration=state.get("inspiration", ""),
            count=state.get("count") or 3,
            style_prompt=state.get("style_prompt"),
            plot_prompt=state.get("plot_prompt"),
            generation_profile=generation_profile,
            previous_output=state.get("previous_output"),
            feedback=state.get("feedback"),
        )
        await self.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name=artifact_name,
            markdown=markdown,
        )
        return {
            "latest_artifacts": [artifact_name],
            "persist_payload": {"markdown": markdown},
        }

    async def _generate_selection_rewrite(self, state: NovelWorkflowState) -> str:
        current_bible = state.get("current_bible", {})
        state_for_context: NovelWorkflowState = {
            **state,
            "text_before_cursor": (
                f"{state.get('text_before_selection', '')}\n"
                f"{state.get('selected_text', '')}"
            ),
        }
        selected_context = await self._select_writing_context(state_for_context, current_bible)
        generation_profile = self._generation_profile_obj(state)
        objective_card = build_chapter_objective_card(
            generation_profile,
            current_chapter_context=state.get("current_chapter_context", ""),
            outline_detail=selected_context.outline_detail,
        )
        system_prompt = assemble_writing_context(
            voice_profile_markdown=state.get("style_prompt"),
            story_engine_markdown=state.get("plot_prompt"),
            generation_profile=generation_profile,
            intensity_profile=build_intensity_profile(generation_profile),
            chapter_objective_card=objective_card,
            sections=WritingContextSections(
                description=state.get("project_description", ""),
                world_building=selected_context.world_building,
                characters_blueprint=selected_context.characters_blueprint,
                outline_master=selected_context.outline_master,
                outline_detail=selected_context.outline_detail,
                characters_status=selected_context.characters_status,
                runtime_state=selected_context.runtime_state,
                runtime_threads=selected_context.runtime_threads,
                story_summary=selected_context.story_summary,
                active_character_focus=selected_context.active_character_focus,
            ),
            length_preset=state.get("length_preset", "long"),
            content_length=state.get("total_content_length", 0),
        )
        parts: list[str] = []
        if state.get("previous_chapter_context", "").strip():
            parts.append(f"## 前序章节\n\n{state.get('previous_chapter_context', '')}")
        if state.get("current_chapter_context", "").strip():
            parts.append(f"## 当前章节\n\n{state.get('current_chapter_context', '')}")
        if selected_context.active_character_focus.strip():
            parts.append("# Active Character Focus\n\n" + selected_context.active_character_focus)
        if state.get("text_before_selection", "").strip():
            parts.append(f"## 选区前文\n\n{state.get('text_before_selection', '')[-3000:]}")
        parts.append(
            "## 选中文本\n\n"
            f"{state.get('selected_text', '')}"
        )
        if state.get("text_after_selection", "").strip():
            parts.append(f"## 选区后文\n\n{state.get('text_after_selection', '')[:3000]}")
        parts.append(
            "## 修改要求\n\n"
            f"{state.get('rewrite_instruction', '').strip() or '在不改变原意的前提下优化表达。'}\n\n"
            "只输出改写后的选中文本。不要生成选区后的内容，不要输出解释、标题、引号或 Markdown 包装。"
        )
        return await self._call_prompt(
            system_prompt=system_prompt,
            user_context="\n\n---\n\n".join(parts),
            mode="immersion",
        )

    async def _write_chapter_from_beats(
        self,
        state: NovelWorkflowState,
    ) -> tuple[str, list[str]]:
        current_bible = state.get("current_bible", {})
        selected_context = await self._select_writing_context(state, current_bible)
        focused_bible = selected_context.as_bible()
        beats = [
            _BEAT_LINE_RE.sub("", line.strip())
            for line in state.get("beats_markdown", "").splitlines()
            if line.strip()
        ]
        warnings = list(state.get("warnings", []))
        prose_parts: list[str] = []

        for index, beat in enumerate(beats):
            accepted = ""
            for attempt in range(3):
                prose_candidate = await self.beat_agent.expand(
                    state=state,
                    current_bible=focused_bible,
                    generation_profile=self._generation_profile_obj(state),
                    beat=beat,
                    beat_index=index,
                    total_beats=len(beats),
                    preceding_beats_prose="".join(prose_parts),
                    previous_output=accepted or None,
                    regenerating=attempt > 0,
                )
                continuity = await self.continuity_agent.review(
                    prose_markdown=prose_candidate,
                    current_bible=focused_bible,
                    current_chapter_context=state.get("current_chapter_context", ""),
                    previous_chapter_context=state.get("previous_chapter_context", ""),
                    beat=beat,
                )
                verdict = self.continuity_agent.extract_verdict(continuity)
                if verdict == "pass":
                    accepted = prose_candidate
                    break
                if attempt == 2:
                    warnings.append(f"beat_{index}_continuity_warning")
                    accepted = prose_candidate
            prose_parts.append(accepted)

        return "".join(prose_parts), warnings

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

    async def _call_prompt(
        self,
        *,
        system_prompt: str,
        user_context: str,
        mode: str,
    ) -> str:
        if self.should_pause is not None and self.should_pause():
            raise NovelWorkflowAwaitingHuman("manual_pause")
        content = await self.llm_complete(
            system_prompt=system_prompt,
            user_context=user_context,
            mode=mode,
        )
        return re.sub(r"<think>.*?(?:</think>\n*|\Z)", "", content, flags=re.DOTALL).strip()

    async def _set_stage(self, stage: str | None) -> None:
        if self.stage_callback is not None:
            await self.stage_callback(stage)

    def _generation_profile_obj(self, state: NovelWorkflowState):
        from app.schemas.prompt_profiles import GenerationProfile, default_generation_profile

        payload = state.get("generation_profile")
        if payload:
            return GenerationProfile.model_validate(payload)
        return default_generation_profile()
