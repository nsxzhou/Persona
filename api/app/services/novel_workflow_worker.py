from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.domain_errors import NotFoundError
from app.db.models import ProviderConfig
from app.schemas.novel_workflows import NOVEL_WORKFLOW_STAGE_PREPARING
from app.schemas.project_chapters import ProjectChapterUpdate
from app.schemas.projects import ProjectBibleUpdate
from app.services.llm_provider import LLMProviderService
from app.services.novel_workflow_checkpointer import NovelWorkflowCheckpointerFactory
from app.services.novel_workflow_pipeline import (
    NovelWorkflowAwaitingHuman,
    NovelWorkflowPipeline,
    NovelWorkflowPipelineResult,
)
from app.services.novel_workflow_storage import NovelWorkflowStorageService
from app.services.novel_workflows import NovelWorkflowService
from app.services.plot_profiles import PlotProfileService
from app.services.project_chapters import ProjectChapterService
from app.services.projects import ProjectService
from app.services.style_profiles import StyleProfileService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NovelWorkflowRunContext:
    provider: ProviderConfig | None
    model_name: str | None
    initial_state: dict[str, object]


class NovelWorkflowJobExecutor:
    def __init__(self) -> None:
        self.job_service = NovelWorkflowService()
        self.checkpointer_factory = NovelWorkflowCheckpointerFactory()
        self.storage_service = NovelWorkflowStorageService()
        self.project_service = ProjectService()
        self.project_chapter_service = ProjectChapterService()
        self.style_profile_service = StyleProfileService()
        self.plot_profile_service = PlotProfileService()
        self.llm_service = LLMProviderService()
        self._pause_events: dict[str, asyncio.Event] = {}
        self._worker_id = f"novel-workflow-worker-{uuid.uuid4()}"

    async def aclose(self) -> None:
        await self.checkpointer_factory.aclose()

    async def process_next_pending(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> bool:
        worker_id = self._worker_id
        run_id = await self._claim_next_pending_run(session_factory, worker_id=worker_id)
        if run_id is None:
            return False
        await self._run_claimed_job(session_factory, run_id)
        return True

    async def _claim_next_pending_run(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        worker_id: str,
    ) -> str | None:
        settings = get_settings()
        async with session_factory.begin() as session:
            return await self.job_service.claim_job_for_worker(
                session,
                worker_id=worker_id,
                max_attempts=settings.style_analysis_max_attempts,
            )

    async def _run_claimed_job(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        run_id: str,
    ) -> None:
        current_stage: str | None = NOVEL_WORKFLOW_STAGE_PREPARING
        current_checkpoint_kind: str | None = None
        pause_event = asyncio.Event()
        self._pause_events[run_id] = pause_event
        stop_heartbeat = asyncio.Event()
        heartbeat_task = asyncio.create_task(
            self._run_stage_heartbeat_loop(
                session_factory,
                run_id,
                get_stage=lambda: current_stage,
                get_checkpoint_kind=lambda: current_checkpoint_kind,
                stop_event=stop_heartbeat,
                interval_seconds=self._heartbeat_interval_seconds(),
            )
        )

        async def stage_callback(stage: str | None) -> None:
            nonlocal current_stage
            current_stage = stage
            await self._touch_run_stage(
                session_factory,
                run_id,
                stage=current_stage,
                checkpoint_kind=current_checkpoint_kind,
            )

        try:
            context = await self._load_run_context(session_factory, run_id)
            await self.storage_service.append_job_log(
                run_id,
                f"[Workflow] starting {context.initial_state['intent_type']}",
            )
            pipeline = await self._build_pipeline(
                provider=context.provider,
                model_name=context.model_name,
                stage_callback=stage_callback,
                should_pause=pause_event.is_set,
                decision_loader=lambda _target_run_id: context.initial_state.get("decision_payload"),
            )
            result = await pipeline.run(
                run_id=run_id,
                initial_state=context.initial_state,
            )
            current_checkpoint_kind = result.checkpoint_kind
            await self._persist_pipeline_result(
                session_factory,
                run_id,
                result=result,
            )
            await self.storage_service.append_job_log(run_id, "[Workflow] completed successfully")
            await self.checkpointer_factory.delete_thread(run_id)
        except NovelWorkflowAwaitingHuman as exc:
            current_checkpoint_kind = exc.checkpoint_kind
            await self.storage_service.append_job_log(
                run_id,
                f"[Workflow] waiting for human decision at {current_checkpoint_kind}",
            )
            await self._mark_run_paused(
                session_factory,
                run_id,
                stage=current_stage,
                checkpoint_kind=current_checkpoint_kind,
            )
        except Exception as exc:
            logger.exception("novel workflow run failed", extra={"run_id": run_id})
            await self.storage_service.append_job_log(
                run_id,
                f"[Workflow] failed: {exc}",
            )
            await self._mark_run_failed(
                session_factory,
                run_id,
                error_message=str(exc),
            )
        finally:
            stop_heartbeat.set()
            await heartbeat_task
            self._pause_events.pop(run_id, None)

    def _heartbeat_interval_seconds(self) -> float:
        stale_timeout_seconds = max(1, get_settings().style_analysis_stale_timeout_seconds)
        return max(0.2, min(30.0, stale_timeout_seconds / 3))

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
        while not stop_event.is_set():
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
                break
            except TimeoutError:
                stage = get_stage()
                if stage is None:
                    continue
                try:
                    await self._touch_run_stage(
                        session_factory,
                        run_id,
                        stage=stage,
                        checkpoint_kind=get_checkpoint_kind(),
                    )
                except Exception:
                    logger.exception(
                        "Failed to send periodic novel workflow heartbeat",
                        extra={"run_id": run_id, "stage": stage},
                    )

    async def _build_pipeline(
        self,
        *,
        provider: ProviderConfig | None,
        model_name: str | None,
        stage_callback,
        should_pause=None,
        decision_loader=None,
    ) -> NovelWorkflowPipeline:
        async def llm_complete(*, system_prompt: str, user_context: str, mode: str) -> str:
            if provider is None:
                raise NotFoundError("工作流缺少可用 Provider")
            return await self.llm_service.invoke_completion(
                provider_config=provider,
                system_prompt=system_prompt,
                user_context=user_context,
                model_name=model_name,
                injection_mode=mode,  # "analysis" / "immersion"
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

    async def _touch_run_stage(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        run_id: str,
        *,
        stage: str | None,
        checkpoint_kind: str | None,
    ) -> None:
        async with session_factory() as session:
            pause_requested_at = await self.job_service.heartbeat_run(
                session,
                run_id,
                stage=stage,
                checkpoint_kind=checkpoint_kind,
            )
            await session.commit()
            if pause_requested_at is not None:
                pause_event = self._pause_events.get(run_id)
                if pause_event is not None:
                    pause_event.set()

    async def _load_run_context(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        run_id: str,
    ) -> NovelWorkflowRunContext:
        async with session_factory() as session:
            run = await self.job_service.repository.get_by_id(session, run_id)
            if run is None:
                raise NotFoundError("工作流任务不存在")
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
            if project is not None and project.style_profile_id:
                style_profile = await self.style_profile_service.get_or_404(
                    session,
                    project.style_profile_id,
                    user_id=run.user_id,
                )
                style_prompt = style_profile.voice_profile_payload
            if project is not None and project.plot_profile_id:
                plot_profile = await self.plot_profile_service.get_or_404(
                    session,
                    project.plot_profile_id,
                    user_id=run.user_id,
                )
                plot_prompt = plot_profile.story_engine_payload

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
            run = await self.job_service.repository.get_by_id(session, run_id)
            if run is None:
                raise NotFoundError("工作流任务不存在")
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
            await self.job_service.mark_run_succeeded(
                session,
                run_id,
                latest_artifacts=result.latest_artifacts,
                warnings=result.warnings,
            )

    async def _mark_run_paused(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        run_id: str,
        *,
        stage: str | None,
        checkpoint_kind: str | None,
    ) -> None:
        async with session_factory.begin() as session:
            await self.job_service.mark_run_paused(
                session,
                run_id,
                stage=stage,
                checkpoint_kind=checkpoint_kind,
            )

    async def _mark_run_failed(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        run_id: str,
        *,
        error_message: str,
    ) -> bool:
        async with session_factory.begin() as session:
            return await self.job_service.mark_run_failed(
                session,
                run_id,
                error_message=error_message,
                max_attempts=get_settings().style_analysis_max_attempts,
            )

    async def fail_stale_running_jobs(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        stale_after_seconds: int,
    ) -> None:
        async with session_factory.begin() as session:
            await self.job_service.recover_stale_runs(
                session,
                stale_after_seconds=stale_after_seconds,
                max_attempts=get_settings().style_analysis_max_attempts,
            )

    async def run_worker(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        poll_interval_seconds: float,
        max_poll_interval_seconds: float | None = None,
    ) -> None:
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be greater than 0")
        max_poll_interval_seconds = max_poll_interval_seconds or poll_interval_seconds
        if max_poll_interval_seconds < poll_interval_seconds:
            max_poll_interval_seconds = poll_interval_seconds
        settings = get_settings()
        last_stale_check = 0.0
        stale_check_interval = max(
            5.0,
            float(settings.style_analysis_stale_timeout_seconds) / 3.0,
        )
        current_interval = poll_interval_seconds
        while True:
            now = time.monotonic()
            if now - last_stale_check >= stale_check_interval:
                await self.fail_stale_running_jobs(
                    session_factory,
                    stale_after_seconds=settings.style_analysis_stale_timeout_seconds,
                )
                last_stale_check = now
            processed = await self.process_next_pending(session_factory)
            if processed:
                current_interval = poll_interval_seconds
                continue
            await asyncio.sleep(current_interval)
            current_interval = min(max_poll_interval_seconds, current_interval * 2)


NovelWorkflowWorkerService = NovelWorkflowJobExecutor
