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
    BeatAgent,
    CharacterBlueprintAgent,
    ChapterPlanAgent,
    ConceptAgent,
    ContextSelectorAgent,
    ContinuityAgent,
    EditorAgent,
    MemorySyncAgent,
    Orchestrator,
    OutlineAgent,
    WorldBuildingAgent,
)
from app.services.novel_workflow_storage import NovelWorkflowStorageService


LLMComplete = Callable[..., Awaitable[str]]
DecisionLoader = Callable[[str], dict[str, Any] | None]
StageCallback = Callable[[str | None], Awaitable[None]]

_BEAT_LINE_RE = re.compile(r"^\s*[-*+]?\s*")
_BUNDLE_SECTION_RE = re.compile(
    r"(?ms)^## (?P<name>[a-z_]+)\n(?P<body>.*?)(?=^## [a-z_]+\n|\Z)"
)


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
        self.context_selector = ContextSelectorAgent()
        self.concept_agent = ConceptAgent(agent_llm)
        self.outline_agent = OutlineAgent(agent_llm)
        self.world_building_agent = WorldBuildingAgent(agent_llm)
        self.character_blueprint_agent = CharacterBlueprintAgent(agent_llm)
        self.chapter_plan_agent = ChapterPlanAgent(agent_llm)
        self.beat_agent = BeatAgent(agent_llm)
        self.continuity_agent = ContinuityAgent(agent_llm)
        self.editor_agent = EditorAgent(agent_llm)
        self.memory_sync_agent = MemorySyncAgent(agent_llm)
        self._simple_intent_handlers = {
            "section_generate": self._handle_section_generate,
            "volume_generate": self._handle_volume_generate,
            "volume_chapters_generate": self._handle_volume_chapters_generate,
            "continuation_write": self._handle_continuation_write,
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
        builder.add_node("run_project_bootstrap", self._run_project_bootstrap)
        builder.add_node("review_outline_bundle", self._review_outline_bundle)
        builder.add_node("finalize_project_bootstrap", self._finalize_project_bootstrap)
        builder.add_node("run_concept_bootstrap", self._run_concept_bootstrap)
        builder.add_node("run_simple_intent", self._run_simple_intent)

        builder.add_edge(START, "prepare_input")
        builder.add_edge("prepare_input", "route_intent")
        builder.add_conditional_edges(
            "route_intent",
            self._select_intent_node,
            [
                "run_project_bootstrap",
                "run_concept_bootstrap",
                "run_simple_intent",
            ],
        )

        builder.add_edge("run_project_bootstrap", "review_outline_bundle")
        builder.add_edge("review_outline_bundle", "finalize_project_bootstrap")
        builder.add_edge("finalize_project_bootstrap", END)

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

    async def _run_project_bootstrap(self, state: NovelWorkflowState) -> dict[str, Any]:
        await self._set_stage(NOVEL_WORKFLOW_STAGE_GENERATING)
        context = self.context_selector.select(state)
        generation_profile = self._generation_profile_obj(state)
        outline_master = await self.outline_agent.generate(
            section="outline_master",
            context=context,
            style_prompt=state.get("style_prompt"),
            plot_prompt=state.get("plot_prompt"),
            generation_profile=generation_profile,
            length_preset=state.get("length_preset", "long"),
        )
        world_building = await self.world_building_agent.generate(
            section="world_building",
            context={**context, "outline_master": outline_master},
            style_prompt=state.get("style_prompt"),
            plot_prompt=state.get("plot_prompt"),
            generation_profile=generation_profile,
            length_preset=state.get("length_preset", "long"),
        )
        characters_blueprint = await self.character_blueprint_agent.generate(
            section="characters_blueprint",
            context={
                **context,
                "world_building": world_building,
                "outline_master": outline_master,
            },
            style_prompt=state.get("style_prompt"),
            plot_prompt=state.get("plot_prompt"),
            generation_profile=generation_profile,
            length_preset=state.get("length_preset", "long"),
        )
        outline_detail = await self.chapter_plan_agent.generate(
            section="outline_detail",
            context={
                **context,
                "world_building": world_building,
                "characters_blueprint": characters_blueprint,
                "outline_master": outline_master,
            },
            style_prompt=state.get("style_prompt"),
            plot_prompt=state.get("plot_prompt"),
            generation_profile=generation_profile,
            length_preset=state.get("length_preset", "long"),
        )
        characters_status = await self.character_blueprint_agent.generate(
            section="characters_status",
            context={
                **context,
                "world_building": world_building,
                "characters_blueprint": characters_blueprint,
                "outline_master": outline_master,
                "outline_detail": outline_detail,
            },
            style_prompt=None,
            plot_prompt=None,
            generation_profile=None,
        )
        runtime_state = await self.memory_sync_agent.generate_section(
            section="runtime_state",
            context={
                **context,
                "world_building": world_building,
                "characters_blueprint": characters_blueprint,
                "outline_master": outline_master,
                "outline_detail": outline_detail,
                "characters_status": characters_status,
            },
        )
        runtime_threads = await self.memory_sync_agent.generate_section(
            section="runtime_threads",
            context={
                **context,
                "world_building": world_building,
                "characters_blueprint": characters_blueprint,
                "outline_master": outline_master,
                "outline_detail": outline_detail,
                "characters_status": characters_status,
                "runtime_state": runtime_state,
            },
        )
        await self.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name="outline_master",
            markdown=outline_master,
        )
        await self.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name="world_building",
            markdown=world_building,
        )
        await self.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name="characters_blueprint",
            markdown=characters_blueprint,
        )
        await self.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name="outline_detail",
            markdown=outline_detail,
        )
        bundle = self._format_outline_bundle(
            outline_master=outline_master,
            world_building=world_building,
            characters_blueprint=characters_blueprint,
            outline_detail=outline_detail,
            characters_status=characters_status,
            runtime_state=runtime_state,
            runtime_threads=runtime_threads,
        )
        await self.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name="outline_bundle",
            markdown=bundle,
        )
        return {
            "outline_master": outline_master,
            "world_building": world_building,
            "characters_blueprint": characters_blueprint,
            "outline_detail": outline_detail,
            "characters_status": characters_status,
            "runtime_state": runtime_state,
            "runtime_threads": runtime_threads,
            "checkpoint_kind": "outline_bundle",
            "latest_artifacts": ["outline_bundle"],
        }

    async def _review_outline_bundle(self, state: NovelWorkflowState) -> dict[str, Any]:
        await self._set_stage(NOVEL_WORKFLOW_STAGE_WAITING_DECISION)
        decision = self.decision_loader(state["run_id"])
        if not decision or decision.get("artifact_name") != "outline_bundle":
            raise NovelWorkflowAwaitingHuman("outline_bundle")

        if decision.get("action") == "revise" and decision.get("edited_markdown"):
            bundle_fields = self._parse_outline_bundle(decision["edited_markdown"])
            return {**bundle_fields, "checkpoint_kind": None}
        return {"checkpoint_kind": None}

    async def _finalize_project_bootstrap(self, state: NovelWorkflowState) -> dict[str, Any]:
        await self._set_stage(NOVEL_WORKFLOW_STAGE_PERSISTING)
        return {
            "persist_payload": {
                "project_bible": {
                    "world_building": state.get("world_building", ""),
                    "characters_blueprint": state.get("characters_blueprint", ""),
                    "outline_master": state.get("outline_master", ""),
                    "outline_detail": state.get("outline_detail", ""),
                    "characters_status": state.get("characters_status", ""),
                    "runtime_state": state.get("runtime_state", ""),
                    "runtime_threads": state.get("runtime_threads", ""),
                    "story_summary": state.get("story_summary", ""),
                }
            }
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

    async def _handle_continuation_write(self, state: NovelWorkflowState, current_bible: dict[str, str], generation_profile: Any) -> dict[str, Any]:
        artifact_name = "prose_markdown"
        markdown = await self._generate_continuation(state)
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
        markdown = await self.beat_agent.expand(
            state=state,
            current_bible=current_bible,
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

    async def _generate_continuation(self, state: NovelWorkflowState) -> str:
        current_bible = state.get("current_bible", {})
        generation_profile = self._generation_profile_obj(state)
        objective_card = build_chapter_objective_card(
            generation_profile,
            current_chapter_context=state.get("current_chapter_context", ""),
            outline_detail=current_bible.get("outline_detail", ""),
        )
        system_prompt = assemble_writing_context(
            voice_profile_markdown=state.get("style_prompt"),
            story_engine_markdown=state.get("plot_prompt"),
            generation_profile=generation_profile,
            intensity_profile=build_intensity_profile(generation_profile),
            chapter_objective_card=objective_card,
            sections=WritingContextSections(
                description=state.get("project_description", ""),
                world_building=current_bible.get("world_building", ""),
                characters_blueprint=current_bible.get("characters_blueprint", ""),
                outline_master=current_bible.get("outline_master", ""),
                outline_detail=current_bible.get("outline_detail", ""),
                characters_status=current_bible.get("characters_status", ""),
                runtime_state=current_bible.get("runtime_state", ""),
                runtime_threads=current_bible.get("runtime_threads", ""),
            ),
            length_preset=state.get("length_preset", "long"),
            content_length=state.get("total_content_length", 0),
        )
        parts: list[str] = []
        if state.get("previous_chapter_context", "").strip():
            parts.append(f"## 前序章节\n\n{state.get('previous_chapter_context', '')}")
        if state.get("current_chapter_context", "").strip():
            parts.append(f"## 当前章节\n\n{state.get('current_chapter_context', '')}")
        parts.append(
            "请从以下当前章节光标位置继续写作，保持自然衔接：\n\n"
            f"{state.get('text_before_cursor', '')}"
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
                    current_bible=current_bible,
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
                    current_bible=current_bible,
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

    @staticmethod
    def _format_outline_bundle(**sections: str) -> str:
        ordered_keys = [
            "outline_master",
            "world_building",
            "characters_blueprint",
            "outline_detail",
            "characters_status",
            "runtime_state",
            "runtime_threads",
        ]
        parts = [f"## {key}\n{sections.get(key, '').strip()}" for key in ordered_keys]
        return "\n\n".join(parts).strip()

    @staticmethod
    def _parse_outline_bundle(markdown: str) -> dict[str, str]:
        parsed: dict[str, str] = {}
        for match in _BUNDLE_SECTION_RE.finditer(markdown.strip()):
            parsed[match.group("name")] = match.group("body").strip()
        return parsed
