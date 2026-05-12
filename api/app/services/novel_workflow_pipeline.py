from __future__ import annotations

import json
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
from app.prompts.imported_chapter_rewrite import (
    IMPORTED_CHAPTER_FULL_REWRITE_INTENT,
    build_imported_chapter_rewrite_system_prompt,
    build_imported_chapter_rewrite_user_context,
    build_imported_context_manifest,
    state_chapter_content,
    state_chapter_title,
    state_imported_chapter,
    validate_imported_chapter_rewrite_output,
)
from app.prompts.outline import (
    build_volume_generate_system_prompt,
    build_volume_generate_user_message,
)
from app.prompts.section_router import build_section_system_prompt, build_section_user_message
from app.prompts.prompt_asset_init import (
    build_prompt_asset_init_system_prompt,
    build_prompt_asset_init_user_message,
    parse_prompt_asset_init_response,
    render_prompt_asset_suggestions_markdown,
)
from app.schemas.novel_workflows import (
    NOVEL_WORKFLOW_STAGE_GENERATING,
    NOVEL_WORKFLOW_STAGE_PERSISTING,
    NOVEL_WORKFLOW_STAGE_PREPARING,
    NOVEL_WORKFLOW_STAGE_WAITING_DECISION,
)
from app.schemas.prompt_profiles import build_chapter_objective_card, build_intensity_profile
from app.services.outline_parser import parse_outline
from app.services.context_assembly import (
    WritingContextSections,
    WritingPromptAssetLayer,
    assemble_writing_context,
)
from app.services.prompt_stack import PromptStackSelection
from app.services.beat_parser import parse_beats_markdown
from app.services.chapter_rewrite_patches import (
    apply_chapter_rewrite_patches,
    parse_chapter_rewrite_patches,
)
from app.services.prose_validation import validate_limited_third_prose
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

_TOP_LEVEL_HEADING_RE = re.compile(r"^#(?!#)\s+.+$")
_IMPORTED_ACTIVE_CHARACTER_SAMPLE_CHARS = 2_000
CHAPTER_REWRITE_ARTIFACT = "chapter_rewrite_markdown"
CHAPTER_REWRITE_PATCHES_ARTIFACT = "chapter_rewrite_patches_markdown"
_CHAPTER_REWRITE_PATCH_MAX_ATTEMPTS = 3


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
        self._simple_intent_handlers = {
            "section_generate": self._handle_section_generate,
            "volume_generate": self._handle_volume_generate,
            "volume_chapters_generate": self._handle_volume_chapters_generate,
            "selection_rewrite": self._handle_selection_rewrite,
            "chapter_enrichment_rewrite": self._handle_chapter_enrichment_rewrite,
            IMPORTED_CHAPTER_FULL_REWRITE_INTENT: self._handle_imported_chapter_full_rewrite,
            "beats_generate": self._handle_beats_generate,
            "beat_expand": self._handle_beat_expand,
            "chapter_expand": self._handle_chapter_expand,
            "memory_refresh": self._handle_memory_refresh,
            "prompt_asset_init": self._handle_prompt_asset_init,
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
        if validate_limited_third_prose(prose_markdown):
            warnings.append("limited_third_pov_retry")
            prose_markdown, retry_warnings = await self._write_chapter_from_beats(
                {
                    **state,
                    "previous_output": prose_markdown,
                    "feedback": "请严格保持限制性第三人称视角，不要使用括号式内心独白或第一人称内心句式。",
                }
            )
            warnings.extend(retry_warnings)
            if validate_limited_third_prose(prose_markdown):
                raise ValueError("限制性第三人称视角校验失败")
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
                current_bible.get("characters_blueprint", ""),
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

    async def _handle_chapter_enrichment_rewrite(self, state: NovelWorkflowState, current_bible: dict[str, str], generation_profile: Any) -> dict[str, Any]:
        original = self._chapter_enrichment_rewrite_source_text(state)
        patches_markdown, markdown = await self._generate_valid_chapter_rewrite_patches(
            state=state,
            original=original,
            generator=self._generate_chapter_enrichment_rewrite,
        )
        await self.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name=CHAPTER_REWRITE_PATCHES_ARTIFACT,
            markdown=patches_markdown,
        )
        await self.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name=CHAPTER_REWRITE_ARTIFACT,
            markdown=markdown,
        )
        return {
            "latest_artifacts": [CHAPTER_REWRITE_ARTIFACT, CHAPTER_REWRITE_PATCHES_ARTIFACT],
            "persist_payload": {
                "markdown": markdown,
                "patches_markdown": patches_markdown,
            },
        }

    async def _handle_imported_chapter_full_rewrite(self, state: NovelWorkflowState, current_bible: dict[str, str], generation_profile: Any) -> dict[str, Any]:
        original = state_chapter_content(state)
        patches_markdown, markdown = await self._generate_valid_chapter_rewrite_patches(
            state=state,
            original=original,
            generator=self._generate_imported_chapter_full_rewrite,
        )
        validation_warnings = validate_imported_chapter_rewrite_output(
            output=markdown,
            original=original,
            target_title=state_chapter_title(state),
            next_chapter=state_imported_chapter(state, "imported_next_chapter"),
            user_instruction=state.get("rewrite_instruction", ""),
        )
        warnings = [*state.get("warnings", []), *validation_warnings]
        for warning in validation_warnings:
            await self.storage_service.append_job_log(
                state["run_id"],
                f"[Warning] imported_chapter_full_rewrite: {warning}",
            )
        await self.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name=CHAPTER_REWRITE_PATCHES_ARTIFACT,
            markdown=patches_markdown,
        )
        await self.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name=CHAPTER_REWRITE_ARTIFACT,
            markdown=markdown,
        )
        return {
            "latest_artifacts": [CHAPTER_REWRITE_ARTIFACT, CHAPTER_REWRITE_PATCHES_ARTIFACT],
            "persist_payload": {
                "markdown": markdown,
                "patches_markdown": patches_markdown,
            },
            "warnings": warnings,
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
            prompt_stack_manifest=_state_prompt_stack_manifest(state),
            prompt_asset_layers=_state_prompt_asset_layers(state),
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

    async def _handle_chapter_expand(self, state: NovelWorkflowState, current_bible: dict[str, str], generation_profile: Any) -> dict[str, Any]:
        artifact_name = "prose_markdown"
        focused_bible = (
            await self._select_writing_context(state, current_bible)
        ).as_bible()
        beats = [beat.strip() for beat in state.get("beats", []) if beat.strip()]
        if not beats:
            beats = parse_beats_markdown(state.get("beats_markdown", ""))
        markdown = await self.beat_agent.expand_chapter(
            state=state,
            current_bible=focused_bible,
            generation_profile=generation_profile,
            beats=beats,
            previous_output=state.get("previous_output"),
            user_feedback=state.get("feedback"),
            regenerating=bool(state.get("previous_output") or state.get("feedback")),
            prompt_stack_manifest=_state_prompt_stack_manifest(state),
            prompt_asset_layers=_state_prompt_asset_layers(state),
        )
        try:
            review_raw = await self.beat_agent.review_chapter_expansion(
                beats=beats,
                prose_markdown=markdown,
            )
        except Exception:
            review_raw = json.dumps(
                {"issues": ["章节审校未完成：审校调用失败，已保留生成正文"]},
                ensure_ascii=False,
            )
        review_issues = _parse_chapter_expand_review_issues(review_raw)
        await self.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name=artifact_name,
            markdown=markdown,
        )
        await self.storage_service.write_stage_markdown_artifact(
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

    async def _handle_prompt_asset_init(self, state: NovelWorkflowState, current_bible: dict[str, str], generation_profile: Any) -> dict[str, Any]:
        artifact_name = "prompt_asset_suggestions"
        raw = await self._call_prompt(
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
        await self.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name=artifact_name,
            markdown=markdown,
        )
        return {
            "latest_artifacts": [artifact_name],
            "persist_payload": {"markdown": markdown},
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
            prompt_asset_layers=_state_prompt_asset_layers(state),
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
            prompt_stack_manifest=_state_prompt_stack_manifest(state),
        )

    async def _generate_chapter_enrichment_rewrite(self, state: NovelWorkflowState) -> str:
        chapter_content = self._chapter_enrichment_rewrite_source_text(state)
        if not chapter_content.strip():
            raise ValueError("当前章节正文为空，无法改写")
        if len(chapter_content) > 80_000:
            raise ValueError("当前章节过长，v1 暂不支持自动分块改写")

        current_bible = state.get("current_bible", {})
        selected_context = await self._select_writing_context(
            {
                **state,
                "text_before_cursor": chapter_content,
                "current_chapter_context": (
                    state.get("current_chapter_context", "")
                    or chapter_content[:3000]
                ),
            },
            current_bible,
        )
        generation_profile = self._generation_profile_obj(state)
        objective_card = build_chapter_objective_card(
            generation_profile,
            current_chapter_context=state.get("current_chapter_context", ""),
            outline_detail=selected_context.outline_detail,
        )
        system_prompt = (
            assemble_writing_context(
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
                prompt_asset_layers=_state_prompt_asset_layers(state),
                length_preset=state.get("length_preset", "long"),
                content_length=len(chapter_content),
            )
            + self._chapter_rewrite_patch_contract(
                expansion_ratio_percent=state.get("expansion_ratio_percent", 20)
            )
        )
        parts = []
        if state.get("previous_chapter_context", "").strip():
            parts.append(f"## 前序章节\n\n{state.get('previous_chapter_context', '')}")
        if state.get("current_chapter_context", "").strip():
            parts.append(f"## 当前章节定位\n\n{state.get('current_chapter_context', '')}")
        parts.append(f"## 原章节正文\n\n{chapter_content}")
        parts.append(
            "## 用户自由改写指令\n\n"
            f"{state.get('rewrite_instruction', '').strip()}\n\n"
            "按上述指令改写整个章节，但输出必须是 Markdown 补丁，不得输出改写后的完整章节。"
        )
        retry_context = self._chapter_rewrite_retry_context(state)
        if retry_context:
            parts.append(retry_context)
        return await self._call_prompt(
            system_prompt=system_prompt,
            user_context="\n\n---\n\n".join(parts),
            mode="immersion",
            prompt_stack_manifest=_state_prompt_stack_manifest(state),
        )

    async def _generate_imported_chapter_full_rewrite(self, state: NovelWorkflowState) -> str:
        chapter_content = state_chapter_content(state)
        if not chapter_content.strip():
            raise ValueError("当前章节正文为空，无法改写")
        if len(chapter_content) > 80_000:
            raise ValueError("当前章节过长，v1 暂不支持自动分块改写")

        current_bible = state.get("current_bible", {})
        selected_context = await self._select_imported_rewrite_character_context(
            state,
            current_bible,
            chapter_content,
        )
        active_character_focus = selected_context.active_character_focus.strip()
        system_prompt = build_imported_chapter_rewrite_system_prompt(
            voice_profile_markdown=state.get("style_prompt", ""),
            active_character_focus=active_character_focus,
            expansion_ratio_percent=state.get("expansion_ratio_percent", 20),
        )
        previous_chapter = state_imported_chapter(state, "imported_previous_chapter")
        next_chapter = state_imported_chapter(state, "imported_next_chapter")
        user_context = build_imported_chapter_rewrite_user_context(
            target_title=state_chapter_title(state),
            chapter_content=chapter_content,
            previous_chapter=previous_chapter,
            next_chapter=next_chapter,
            rewrite_instruction=state.get("rewrite_instruction", ""),
            expansion_ratio_percent=state.get("expansion_ratio_percent", 20),
        )
        retry_context = self._chapter_rewrite_retry_context(state)
        if retry_context:
            user_context = f"{user_context}\n\n---\n\n{retry_context}"
        return await self._call_prompt(
            system_prompt=system_prompt,
            user_context=user_context,
            mode="immersion",
            prompt_stack_manifest=_merge_prompt_stack_manifest(
                _state_prompt_stack_manifest(state),
                build_imported_context_manifest(
                    state=state,
                    chapter_content=chapter_content,
                    previous_chapter=previous_chapter,
                    next_chapter=next_chapter,
                    voice_profile_markdown=state.get("style_prompt", ""),
                    active_character_focus=active_character_focus,
                    active_character_names=selected_context.active_character_names,
                ),
            ),
        )

    @staticmethod
    def _chapter_enrichment_rewrite_source_text(state: NovelWorkflowState) -> str:
        chapter_snapshot = state.get("chapter_snapshot")
        if isinstance(chapter_snapshot, dict):
            content = chapter_snapshot.get("content", "")
            if isinstance(content, str) and content.strip():
                return content
        return state.get("selected_text", "")

    @staticmethod
    def _chapter_rewrite_patch_contract(*, expansion_ratio_percent: int) -> str:
        return (
            "\n\n## 章节改写 Patch 输出硬规则\n"
            "- 你必须只输出 Markdown 补丁，不得输出改写后的完整章节。\n"
            "- 不输出分析、标题以外的说明、解释、修改总结、JSON 或额外 Markdown 包装。\n"
            "- 顶层标题必须是 `# Chapter Rewrite Patches`。\n"
            "- 每个补丁小节使用 `## Patch 1`、`## Patch 2` 等标题。\n"
            "- Operation 只能是 `insert_after` 或 `replace`。\n"
            "- Anchor 必须是原章节中一个完整自然段的逐字精确文本，且只出现一次。\n"
            "- Anchor 只能定位一个自然段，不能包含空行，不能跨越空行分隔的多个自然段。\n"
            "- New Text 必须放在 ```text 代码块中，可以包含一个或多个新自然段。\n"
            "- insert_after 表示把 New Text 插入到 Anchor 段落后；replace 表示只替换 Anchor 这一个自然段。\n"
            "- 不得重复使用 Anchor，不得使用互相重叠或包含的 Anchor。\n"
            f"- 合成后的净增长至少达到原文字数的 {expansion_ratio_percent}% 目标的 80%；允许超出目标上限。\n"
            "- 如果没有可用补丁，只能输出 `# Chapter Rewrite Patches` 后接 `No patches.`，这会被视为失败。\n"
            "\n"
            "格式示例：\n"
            "# Chapter Rewrite Patches\n\n"
            "## Patch 1\n"
            "Operation: insert_after\n\n"
            "Anchor:\n```text\n<one exact full original paragraph>\n```\n\n"
            "New Text:\n```text\n<one or more new paragraphs>\n```\n"
        )

    async def _generate_valid_chapter_rewrite_patches(
        self,
        *,
        state: NovelWorkflowState,
        original: str,
        generator: Callable[[NovelWorkflowState], Awaitable[str]],
    ) -> tuple[str, str]:
        retry_invalid_output: str | None = None
        retry_validation_error: str | None = None
        for attempt in range(_CHAPTER_REWRITE_PATCH_MAX_ATTEMPTS):
            attempt_state = state
            if retry_invalid_output is not None and retry_validation_error is not None:
                attempt_state = {
                    **state,
                    "chapter_rewrite_retry_invalid_output": retry_invalid_output,
                    "chapter_rewrite_retry_validation_error": retry_validation_error,
                }
            patches_markdown = await generator(attempt_state)
            try:
                markdown = self._synthesize_chapter_rewrite(
                    original=original,
                    patches_markdown=patches_markdown,
                    expansion_ratio_percent=state.get("expansion_ratio_percent", 20),
                )
            except ValueError as exc:
                if attempt == _CHAPTER_REWRITE_PATCH_MAX_ATTEMPTS - 1:
                    raise
                retry_invalid_output = patches_markdown
                retry_validation_error = str(exc)
                continue
            return patches_markdown, markdown
        raise RuntimeError("unreachable chapter rewrite patch retry state")

    @staticmethod
    def _chapter_rewrite_retry_context(state: NovelWorkflowState) -> str:
        invalid_output = (state.get("chapter_rewrite_retry_invalid_output") or "").strip()
        validation_error = (
            state.get("chapter_rewrite_retry_validation_error") or ""
        ).strip()
        if not invalid_output or not validation_error:
            return ""
        return (
            "## 上一次补丁校验失败（必须修正后重试）\n\n"
            f"校验错误：{validation_error}\n\n"
            "上一次无效输出：\n\n"
            f"{invalid_output}\n\n"
            "重试要求：重新输出完整 Markdown 补丁；Anchor 必须是原文中一个完整自然段的逐字精确文本，"
            "且只能定位一个自然段，不能包含空行，不能跨越空行分隔的多个自然段。"
        )

    @staticmethod
    def _synthesize_chapter_rewrite(
        *,
        original: str,
        patches_markdown: str,
        expansion_ratio_percent: int,
    ) -> str:
        patches = parse_chapter_rewrite_patches(patches_markdown)
        return apply_chapter_rewrite_patches(
            original,
            patches,
            expansion_ratio_percent=expansion_ratio_percent,
        )

    async def _write_chapter_from_beats(
        self,
        state: NovelWorkflowState,
    ) -> tuple[str, list[str]]:
        current_bible = state.get("current_bible", {})
        selected_context = await self._select_writing_context(state, current_bible)
        focused_bible = selected_context.as_bible()
        beats = parse_beats_markdown(state.get("beats_markdown", ""))
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
                    user_feedback=state.get("feedback"),
                    regenerating=attempt > 0,
                    prompt_stack_manifest=_state_prompt_stack_manifest(state),
                    prompt_asset_layers=_state_prompt_asset_layers(state),
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


def _state_prompt_stack_manifest(state: dict[str, Any]) -> dict | None:
    prompt_stack = state.get("prompt_stack")
    manifest = getattr(prompt_stack, "manifest", None)
    if manifest is None:
        return None
    if hasattr(manifest, "model_dump"):
        return manifest.model_dump(mode="json")
    if isinstance(manifest, dict):
        return manifest
    return None


def _merge_prompt_stack_manifest(
    prompt_stack_manifest: dict | None,
    imported_context_manifest: dict[str, Any],
) -> dict[str, Any]:
    if prompt_stack_manifest is None:
        return {"imported_rewrite_context": imported_context_manifest}
    return {
        **prompt_stack_manifest,
        "imported_rewrite_context": imported_context_manifest,
    }


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


def _state_prompt_asset_layers(state: dict[str, Any]) -> list[WritingPromptAssetLayer]:
    prompt_stack = state.get("prompt_stack")
    layers = getattr(prompt_stack, "layers", None)
    if not isinstance(layers, list):
        return []
    return [
        WritingPromptAssetLayer(
            key=layer.key,
            title=layer.title,
            content=layer.content,
        )
        for layer in layers
        if getattr(layer, "key", "") in {
            "active_lorebook_entries",
            "active_character_cards",
            "author_notes",
        }
    ]


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
