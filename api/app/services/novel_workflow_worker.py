from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.domain_errors import NotFoundError
from app.db.models import ProviderConfig
from app.schemas.project_chapters import ProjectChapterUpdate
from app.schemas.projects import ProjectBibleUpdate, ProjectPromptAssetResponse
from openai import (
    AuthenticationError as OpenAIAuthenticationError,
    BadRequestError as OpenAIBadRequestError,
    NotFoundError as OpenAINotFoundError,
    UnprocessableEntityError as OpenAIUnprocessableEntityError,
)
from app.services.analysis_worker_lifecycle import (
    BaseAnalysisJobExecutor,
    ShouldPause,
    StageCallback,
)
from app.services.novel_workflow_pipeline import (
    NovelWorkflowAwaitingHuman,
    NovelWorkflowPipeline,
    NovelWorkflowPipelineResult,
)
from app.services.prompt_trace import PromptTraceMessage, PromptTraceRecorder
from app.services.service_graph import (
    NovelWorkflowServiceGraph,
    build_novel_workflow_service_graph,
)

logger = logging.getLogger(__name__)
_IMPORTED_REWRITE_ACTIVATION_SAMPLE_CHARS = 12_000

_NON_RETRYABLE_ERRORS = (
    OpenAINotFoundError,
    OpenAIAuthenticationError,
    OpenAIBadRequestError,
    OpenAIUnprocessableEntityError,
    ValueError,
)


def _is_non_retryable_error(exc: Exception) -> bool:
    """Permanent LLM/API errors that should not be retried."""
    if isinstance(exc, _NON_RETRYABLE_ERRORS):
        return True
    cause = exc.__cause__
    while cause is not None:
        if isinstance(cause, _NON_RETRYABLE_ERRORS):
            return True
        cause = getattr(cause, "__cause__", None)
    return False


@dataclass(frozen=True)
class NovelWorkflowRunContext:
    provider: ProviderConfig | None
    model_name: str | None
    initial_state: dict[str, object]


class NovelWorkflowJobExecutor(BaseAnalysisJobExecutor):
    initial_stage = "preparing"
    pause_exceptions = (NovelWorkflowAwaitingHuman,)
    failure_log_message = "novel workflow run failed"
    heartbeat_failure_log_message = "Failed to send periodic novel workflow heartbeat"
    cleanup_successful_job_artifacts = False
    logger = logger

    def __init__(self, service_graph: NovelWorkflowServiceGraph | None = None) -> None:
        graph = service_graph or build_novel_workflow_service_graph()
        self.workflow_service = graph.workflow_service
        self.lifecycle_service = graph.workflow_lifecycle_service
        self.checkpointer_factory = graph.checkpointer_factory
        self.storage_service = graph.storage_service
        self.project_service = graph.project_service
        self.project_chapter_service = graph.project_chapter_service
        self.prompt_stack_service = graph.prompt_stack_service
        self.style_profile_service = graph.style_profile_service
        self.plot_profile_service = graph.plot_profile_service
        self.llm_service = graph.llm_service
        super().__init__(
            job_service=self.lifecycle_service,
            checkpointer_factory=self.checkpointer_factory,
            storage_service=self.storage_service,
            worker_id_prefix="novel-workflow-worker",
        )

    async def process_run_by_id(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        run_id: str,
    ) -> bool:
        return await self.process_job_by_id(session_factory, run_id)

    def _max_attempts(self) -> int:
        return get_settings().novel_workflow_max_attempts

    def _stale_timeout_seconds(self) -> int:
        return get_settings().novel_workflow_stale_timeout_seconds

    def _is_terminal_error(self, exc: Exception) -> bool:
        return _is_non_retryable_error(exc)

    async def _claim_pending_job_by_id(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
        *,
        worker_id: str,
    ) -> bool:
        async with session_factory.begin() as session:
            return await self.lifecycle_service.claim_job_by_id_for_worker(
                session,
                job_id,
                worker_id=worker_id,
            )

    async def _run_job_to_success(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        run_id: str,
        *,
        stage_callback: StageCallback,
        should_pause: ShouldPause,
        checkpoint_kind_callback: Callable[[str | None], Awaitable[None]] | None = None,
    ) -> None:
        context = await self._load_run_context(session_factory, run_id)
        await self.storage_service.append_job_log(
            run_id,
            f"[Workflow] starting {context.initial_state['intent_type']}",
        )
        pipeline = await self._build_pipeline(
            run_id=run_id,
            intent_type=str(context.initial_state["intent_type"]),
            provider=context.provider,
            model_name=context.model_name,
            stage_getter=lambda: None,
            stage_callback=stage_callback,
            should_pause=should_pause,
            decision_loader=lambda _target_run_id: context.initial_state.get("decision_payload"),
        )
        result = await pipeline.run(
            run_id=run_id,
            initial_state=context.initial_state,
        )
        if checkpoint_kind_callback is not None:
            await checkpoint_kind_callback(result.checkpoint_kind)
        await self._persist_pipeline_result(
            session_factory,
            run_id,
            result=result,
        )
        await self.storage_service.append_job_log(run_id, "[Workflow] completed successfully")
        await self.checkpointer_factory.delete_thread(run_id)

    async def _mark_job_failed(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
        *,
        error_message: str,
        force_terminal: bool = False,
    ) -> bool:
        await self.storage_service.append_job_log(
            job_id,
            f"[Workflow] failed: {error_message}",
        )
        return await super()._mark_job_failed(
            session_factory,
            job_id,
            error_message=error_message,
            force_terminal=force_terminal,
        )

    async def _mark_job_paused(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
        *,
        stage: str | None,
        checkpoint_kind: str | None = None,
    ) -> None:
        await self.storage_service.append_job_log(
            job_id,
            f"[Workflow] waiting for human decision at {checkpoint_kind}",
        )
        await super()._mark_job_paused(
            session_factory,
            job_id,
            stage=stage,
            checkpoint_kind=checkpoint_kind,
        )

    async def _run_stage_heartbeat_loop(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        run_id: str,
        *,
        get_stage: Callable[[], str | None],
        get_checkpoint_kind: Callable[[], str | None],
        stop_event: asyncio.Event,
        interval_seconds: float,
    ) -> None:
        await super()._run_stage_heartbeat_loop(
            session_factory,
            run_id,
            get_stage=get_stage,
            get_checkpoint_kind=get_checkpoint_kind,
            stop_event=stop_event,
            interval_seconds=interval_seconds,
        )

    async def _build_pipeline(
        self,
        *,
        run_id: str,
        intent_type: str,
        provider: ProviderConfig | None,
        model_name: str | None,
        stage_getter,
        stage_callback,
        should_pause=None,
        decision_loader=None,
    ) -> NovelWorkflowPipeline:
        trace_recorder = PromptTraceRecorder(
            run_id=run_id,
            intent_type=intent_type,
            provider_id=provider.id if provider is not None else None,
            provider_label=provider.label if provider is not None else None,
            model_name=model_name or (provider.default_model if provider is not None else None),
            storage_service=self.storage_service,
            stage_getter=stage_getter,
        )

        async def record_prompt_trace(
            *,
            mode: str,
            provider_prompt_override_applied: bool,
            messages: list[PromptTraceMessage],
            started_at,
            completed_at,
            output: str | None,
            error_summary: str | None,
            prompt_stack_manifest: dict | None = None,
        ) -> None:
            if error_summary is not None:
                await trace_recorder.record_error(
                    mode=mode,
                    provider_prompt_override_applied=provider_prompt_override_applied,
                    messages=messages,
                    started_at=started_at,
                    completed_at=completed_at,
                    error_summary=error_summary,
                    prompt_stack_manifest=prompt_stack_manifest,
                )
                return
            await trace_recorder.record_success(
                mode=mode,
                provider_prompt_override_applied=provider_prompt_override_applied,
                messages=messages,
                started_at=started_at,
                completed_at=completed_at,
                output=output or "",
                prompt_stack_manifest=prompt_stack_manifest,
            )

        async def llm_complete(
            *,
            system_prompt: str,
            user_context: str,
            mode: str,
            prompt_stack_manifest: dict | None = None,
        ) -> str:
            if provider is None:
                raise NotFoundError("工作流缺少可用 Provider")
            return await self.llm_service.invoke_completion(
                provider_config=provider,
                system_prompt=system_prompt,
                user_context=user_context,
                model_name=model_name,
                injection_mode=mode,  # "analysis" / "immersion"
                prompt_trace_callback=record_prompt_trace,
                prompt_stack_manifest=prompt_stack_manifest,
            )

        if decision_loader is None:
            decision_loader = lambda _run_id: None
        return NovelWorkflowPipeline(
            llm_complete=llm_complete,
            storage_service=self.storage_service,
            checkpointer=await self.checkpointer_factory.get(),
            decision_loader=decision_loader,
            stage_callback=stage_callback,
            should_pause=should_pause,
        )

    async def _load_run_context(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        run_id: str,
    ) -> NovelWorkflowRunContext:
        async with session_factory() as session:
            run = await self.workflow_service.repository.get_by_id(session, run_id)
            if run is None:
                raise NotFoundError(f"工作流任务不存在: run_id={run_id}")
            request_payload = dict(run.request_payload or {})
            project = run.project
            bible = None
            if project is not None:
                bible = await self.project_service.get_bible_or_404(
                    session,
                    project.id,
                    user_id=run.user_id,
                )
            chapter = run.chapter
            style_prompt = None
            plot_prompt = None
            style_profile_id = request_payload.get("style_profile_id") or (
                project.style_profile_id if project is not None else None
            )
            plot_profile_id = request_payload.get("plot_profile_id") or (
                project.plot_profile_id if project is not None else None
            )
            if project is not None and style_profile_id:
                style_profile = await self.style_profile_service.get_or_404(
                    session,
                    str(style_profile_id),
                    user_id=run.user_id,
                )
                style_prompt = style_profile.voice_profile_payload
            if project is not None and plot_profile_id:
                plot_profile = await self.plot_profile_service.get_or_404(
                    session,
                    str(plot_profile_id),
                    user_id=run.user_id,
                )
                plot_prompt = plot_profile.story_engine_payload

            prompt_stack = None
            prompt_assets: list[ProjectPromptAssetResponse] = []
            if project is not None:
                raw_prompt_assets = await self.prompt_stack_service.list_assets(
                    session,
                    project.id,
                    user_id=run.user_id,
                )
                prompt_assets = [
                    ProjectPromptAssetResponse.model_validate(asset)
                    for asset in raw_prompt_assets
                ]
                activation_user_context = "\n".join(
                    str(request_payload.get(key) or "")
                    for key in (
                        "user_context",
                        "selected_text",
                        "text_after_selection",
                        "rewrite_instruction",
                        "beat",
                        "beats",
                        "preceding_beats_prose",
                        "content_to_check",
                    )
                )
                if request_payload.get("intent_type") == "imported_chapter_full_rewrite":
                    selected_text = str(request_payload.get("selected_text") or "")
                    activation_user_context = "\n".join(
                        part
                        for part in (
                            _sample_text_for_imported_rewrite(selected_text),
                            str(request_payload.get("rewrite_instruction") or ""),
                        )
                        if part
                    )
                prompt_stack = await self.prompt_stack_service.select_for_runtime(
                    session,
                    project.id,
                    user_id=run.user_id,
                    chapter_id=run.chapter_id,
                    current_chapter_context=str(request_payload.get("current_chapter_context") or ""),
                    text_before_cursor=str(
                        (
                            _sample_text_for_imported_rewrite(
                                str(request_payload.get("selected_text") or "")
                            )
                            if request_payload.get("intent_type") == "imported_chapter_full_rewrite"
                            else request_payload.get("text_before_cursor")
                        )
                        or request_payload.get("text_before_selection")
                        or ""
                    ),
                    user_context=activation_user_context,
                )

            enable_editor_pass = False
            model_overrides = request_payload.get("model_overrides")
            if isinstance(model_overrides, dict):
                enable_editor_pass = bool(model_overrides.get("enable_editor_pass"))

            initial_state: dict[str, object] = {
                **request_payload,
                "intent_type": run.intent_type,
                "project_id": run.project_id,
                "chapter_id": run.chapter_id,
                "decision_payload": run.decision_payload,
                "project_name": project.name if project is not None else "",
                "project_description": project.description if project is not None else "",
                "length_preset": project.length_preset if project is not None else "long",
                "style_prompt": style_prompt or "",
                "plot_prompt": plot_prompt or "",
                "generation_profile": request_payload.get("generation_profile")
                or (project.generation_profile_payload if project is not None else None),
                "current_bible": {
                    "world_building": bible.world_building if bible is not None else "",
                    "characters_blueprint": bible.characters_blueprint if bible is not None else "",
                    "outline_master": bible.outline_master if bible is not None else "",
                    "outline_detail": bible.outline_detail if bible is not None else "",
                    "characters_status": bible.characters_status if bible is not None else "",
                    "runtime_state": bible.runtime_state if bible is not None else "",
                    "runtime_threads": bible.runtime_threads if bible is not None else "",
                    "story_summary": bible.story_summary if bible is not None else "",
                },
                "chapter_snapshot": {
                    "title": chapter.title if chapter is not None else "",
                    "content": chapter.content if chapter is not None else "",
                    "summary": chapter.summary if chapter is not None else "",
                    "beats_markdown": chapter.beats_markdown if chapter is not None else "",
                },
                "enable_editor_pass": enable_editor_pass,
                "prompt_stack": prompt_stack,
                "prompt_assets": prompt_assets,
            }
            provider = run.provider or (project.provider if project is not None else None)
            model_name = run.model_name or (project.default_model if project is not None else None)
            return NovelWorkflowRunContext(
                provider=provider,
                model_name=model_name,
                initial_state=initial_state,
            )
    async def _persist_pipeline_result(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        run_id: str,
        *,
        result: NovelWorkflowPipelineResult,
    ) -> None:
        async with session_factory.begin() as session:
            run = await self.workflow_service.repository.get_by_id(session, run_id)
            if run is None:
                raise NotFoundError(f"工作流任务不存在: run_id={run_id}")
            payload = result.persist_payload
            if run.project_id and "project_bible" in payload:
                await self.project_service.update_bible(
                    session,
                    run.project_id,
                    ProjectBibleUpdate(**payload["project_bible"]),
                    user_id=run.user_id,
                )
            if run.project_id and run.chapter_id and "chapter" in payload:
                await self.project_chapter_service.update(
                    session,
                    run.project_id,
                    run.chapter_id,
                    ProjectChapterUpdate(**payload["chapter"]),
                    user_id=run.user_id,
                )
            await self.lifecycle_service.mark_run_succeeded(
                session,
                run_id,
                latest_artifacts=result.latest_artifacts,
                warnings=result.warnings,
            )

def _sample_text_for_imported_rewrite(text: str) -> str:
    stripped = text.strip()
    if len(stripped) <= _IMPORTED_REWRITE_ACTIVATION_SAMPLE_CHARS:
        return stripped
    segment = _IMPORTED_REWRITE_ACTIVATION_SAMPLE_CHARS // 3
    middle_start = max((len(stripped) - segment) // 2, segment)
    return "\n\n".join(
        (
            stripped[:segment],
            stripped[middle_start : middle_start + segment],
            stripped[-segment:],
        )
    )


NovelWorkflowWorkerService = NovelWorkflowJobExecutor
