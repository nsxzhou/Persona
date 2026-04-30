from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.domain_errors import ConflictError, NotFoundError
from app.db.models import NovelWorkflowRun
from app.db.repositories.novel_workflows import NovelWorkflowRepository
from app.schemas.novel_workflows import (
    NOVEL_WORKFLOW_STAGE_PREPARING,
    NOVEL_WORKFLOW_STATUS_FAILED,
    NOVEL_WORKFLOW_STATUS_PAUSED,
    NOVEL_WORKFLOW_STATUS_PENDING,
    NOVEL_WORKFLOW_STATUS_RUNNING,
    NOVEL_WORKFLOW_STATUS_SUCCEEDED,
    NovelWorkflowCreateRequest,
    NovelWorkflowDecisionRequest,
    NovelWorkflowLogsResponse,
)
from app.services.novel_workflow_storage import NovelWorkflowStorageService
from app.services.project_chapters import ProjectChapterService
from app.services.projects import ProjectService
from app.services.provider_configs import ProviderConfigService


def _reset_run_to_pending(
    run: NovelWorkflowRun,
    *,
    target_status: str = NOVEL_WORKFLOW_STATUS_PENDING,
    reset_attempts: bool = False,
    paused_at: datetime | None = None,
) -> None:
    run.status = target_status
    run.stage = None
    run.checkpoint_kind = None
    run.error_message = None
    run.started_at = None
    run.completed_at = None
    run.locked_by = None
    run.locked_at = None
    run.last_heartbeat_at = None
    run.pause_requested_at = None
    run.paused_at = paused_at
    if reset_attempts:
        run.attempt_count = 0


def _normalize_utc_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class NovelWorkflowService:
    def __init__(
        self,
        repository: NovelWorkflowRepository | None = None,
        storage_service: NovelWorkflowStorageService | None = None,
        project_service: ProjectService | None = None,
        project_chapter_service: ProjectChapterService | None = None,
        provider_service: ProviderConfigService | None = None,
    ) -> None:
        self.repository = repository or NovelWorkflowRepository()
        self.storage_service = storage_service or NovelWorkflowStorageService()
        self.project_service = project_service or ProjectService()
        self.project_chapter_service = project_chapter_service or ProjectChapterService()
        self.provider_service = provider_service or ProviderConfigService()

    async def list(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        offset: int = 0,
        limit: int = 50,
    ) -> list[NovelWorkflowRun]:
        limit = min(max(limit, 1), 100)
        return await self.repository.list(session, user_id=user_id, offset=offset, limit=limit)

    async def get_or_404(
        self,
        session: AsyncSession,
        run_id: str,
        *,
        user_id: str,
    ) -> NovelWorkflowRun:
        run = await self.repository.get_by_id(session, run_id, user_id=user_id)
        if run is None:
            raise NotFoundError("工作流任务不存在")
        return run

    async def get_detail_or_404(
        self,
        session: AsyncSession,
        run_id: str,
        *,
        user_id: str,
    ) -> NovelWorkflowRun:
        return await self.get_or_404(session, run_id, user_id=user_id)

    async def get_status_or_404(
        self,
        session: AsyncSession,
        run_id: str,
        *,
        user_id: str,
    ) -> NovelWorkflowRun:
        run = await self.get_or_404(session, run_id, user_id=user_id)
        if await self._reconcile_pause_request_if_unacknowledged(session, run):
            run = await self.get_or_404(session, run_id, user_id=user_id)
        if await self._reconcile_stale_run_if_needed(session, run):
            run = await self.get_or_404(session, run_id, user_id=user_id)
        return run

    async def create(
        self,
        session: AsyncSession,
        payload: NovelWorkflowCreateRequest,
        *,
        user_id: str,
    ) -> NovelWorkflowRun:
        project = None
        chapter_id = payload.chapter_id
        provider_id = payload.provider_id
        model_name = payload.model_name
        if payload.project_id is not None:
            project = await self.project_service.get_or_404(
                session,
                payload.project_id,
                user_id=user_id,
            )
            provider_id = provider_id or project.default_provider_id
            model_name = model_name or project.default_model
        if provider_id is not None:
            await self.provider_service.ensure_enabled(session, provider_id, user_id=user_id)

        request_payload = payload.model_dump(exclude_none=True, mode="json")
        run = await self.repository.create_run(
            session,
            user_id=user_id,
            project_id=payload.project_id,
            chapter_id=chapter_id,
            provider_id=provider_id,
            intent_type=payload.intent_type,
            model_name=model_name,
            request_payload=request_payload,
            pending_status=NOVEL_WORKFLOW_STATUS_PENDING,
        )
        await self.repository.flush(session)
        return run

    async def pause(
        self,
        session: AsyncSession,
        run_id: str,
        *,
        user_id: str,
    ) -> NovelWorkflowRun:
        run = await self.get_or_404(session, run_id, user_id=user_id)
        if run.status == NOVEL_WORKFLOW_STATUS_SUCCEEDED:
            raise ConflictError("工作流已成功完成，无法暂停")
        if run.status == NOVEL_WORKFLOW_STATUS_FAILED:
            raise ConflictError("工作流已失败，无法暂停")
        if run.status == NOVEL_WORKFLOW_STATUS_PAUSED:
            return run
        if run.status == NOVEL_WORKFLOW_STATUS_PENDING:
            _reset_run_to_pending(
                run,
                target_status=NOVEL_WORKFLOW_STATUS_PAUSED,
                paused_at=datetime.now(UTC),
            )
            await session.flush()
            return run
        await self.repository.request_pause(
            session,
            run_id,
            running_status=NOVEL_WORKFLOW_STATUS_RUNNING,
            now=datetime.now(UTC),
        )
        await session.flush()
        refreshed = await self.get_or_404(session, run_id, user_id=user_id)
        await self._reconcile_pause_request_if_unacknowledged(session, refreshed)
        await self._reconcile_stale_run_if_needed(session, refreshed)
        return await self.get_or_404(session, run_id, user_id=user_id)

    async def resume(
        self,
        session: AsyncSession,
        run_id: str,
        *,
        user_id: str,
    ) -> NovelWorkflowRun:
        run = await self.get_or_404(session, run_id, user_id=user_id)
        if run.status == NOVEL_WORKFLOW_STATUS_RUNNING and run.locked_by:
            raise ConflictError("工作流正在运行，无法恢复")
        if run.status == NOVEL_WORKFLOW_STATUS_SUCCEEDED:
            raise ConflictError("工作流已成功完成，无需恢复")
        if run.status == NOVEL_WORKFLOW_STATUS_PAUSED:
            _reset_run_to_pending(run)
            await session.flush()
            return run
        _reset_run_to_pending(run, reset_attempts=True)
        await session.flush()
        return run

    async def submit_decision(
        self,
        session: AsyncSession,
        run_id: str,
        payload: NovelWorkflowDecisionRequest,
        *,
        user_id: str,
    ) -> NovelWorkflowRun:
        run = await self.get_or_404(session, run_id, user_id=user_id)
        if run.status != NOVEL_WORKFLOW_STATUS_PAUSED:
            raise ConflictError("仅暂停中的工作流可以提交人工决策")
        run.decision_payload = payload.model_dump(mode="json")
        _reset_run_to_pending(run)
        await session.flush()
        return run

    async def get_job_logs_or_404(
        self,
        session: AsyncSession,
        run_id: str,
        *,
        user_id: str,
        offset: int = 0,
    ) -> NovelWorkflowLogsResponse:
        await self.get_or_404(session, run_id, user_id=user_id)
        content, next_offset, truncated = await self.storage_service.read_job_logs_incremental(
            run_id,
            offset=offset,
        )
        return NovelWorkflowLogsResponse(
            content=content,
            next_offset=next_offset,
            truncated=truncated,
        )

    async def get_artifact_or_404(
        self,
        session: AsyncSession,
        run_id: str,
        artifact_name: str,
        *,
        user_id: str,
    ) -> str:
        await self.get_or_404(session, run_id, user_id=user_id)
        if not self.storage_service.stage_markdown_artifact_exists(run_id, name=artifact_name):
            raise NotFoundError("工作流产物不存在")
        return await self.storage_service.read_stage_markdown_artifact(
            run_id,
            name=artifact_name,
        )

    async def claim_job_for_worker(
        self,
        session: AsyncSession,
        *,
        worker_id: str,
        max_attempts: int,
    ) -> str | None:
        return await self.repository.claim_pending_run(
            session,
            worker_id=worker_id,
            max_attempts=max_attempts,
            preparing_stage=NOVEL_WORKFLOW_STAGE_PREPARING,
            running_status=NOVEL_WORKFLOW_STATUS_RUNNING,
            pending_status=NOVEL_WORKFLOW_STATUS_PENDING,
            now=datetime.now(UTC),
        )

    async def heartbeat_run(
        self,
        session: AsyncSession,
        run_id: str,
        *,
        stage: str | None,
        checkpoint_kind: str | None,
    ) -> datetime | None:
        return await self.repository.heartbeat(
            session,
            run_id,
            running_status=NOVEL_WORKFLOW_STATUS_RUNNING,
            stage=stage,
            checkpoint_kind=checkpoint_kind,
            now=datetime.now(UTC),
        )

    async def mark_run_paused(
        self,
        session: AsyncSession,
        run_id: str,
        *,
        stage: str | None,
        checkpoint_kind: str | None,
    ) -> None:
        await self.repository.mark_paused(
            session,
            run_id,
            paused_status=NOVEL_WORKFLOW_STATUS_PAUSED,
            now=datetime.now(UTC),
            stage=stage,
            checkpoint_kind=checkpoint_kind,
        )

    async def mark_run_succeeded(
        self,
        session: AsyncSession,
        run_id: str,
        *,
        latest_artifacts: list[str],
        warnings: list[str],
    ) -> None:
        run = await self.repository.get_by_id(session, run_id)
        if run is None:
            raise NotFoundError("工作流任务不存在")
        run.status = NOVEL_WORKFLOW_STATUS_SUCCEEDED
        run.stage = None
        run.checkpoint_kind = None
        run.error_message = None
        run.completed_at = datetime.now(UTC)
        run.locked_by = None
        run.locked_at = None
        run.last_heartbeat_at = None
        run.pause_requested_at = None
        run.latest_artifacts_payload = latest_artifacts
        run.warnings_payload = warnings
        await session.flush()

    async def mark_run_failed(
        self,
        session: AsyncSession,
        run_id: str,
        *,
        error_message: str,
        max_attempts: int,
    ) -> bool:
        run = await self.repository.get_by_id(session, run_id)
        if run is None:
            raise NotFoundError("工作流任务不存在")
        is_terminal = run.attempt_count >= max_attempts
        if is_terminal:
            run.status = NOVEL_WORKFLOW_STATUS_FAILED
            run.error_message = error_message
            run.stage = None
            run.checkpoint_kind = None
            run.completed_at = datetime.now(UTC)
        else:
            _reset_run_to_pending(run)
            run.error_message = error_message
        await session.flush()
        return is_terminal

    async def recover_stale_runs(
        self,
        session: AsyncSession,
        *,
        stale_after_seconds: int,
        max_attempts: int,
    ) -> None:
        await self.repository.recover_stale_runs(
            session,
            cutoff=datetime.now(UTC) - timedelta(seconds=stale_after_seconds),
            max_attempts=max_attempts,
            running_status=NOVEL_WORKFLOW_STATUS_RUNNING,
            paused_status=NOVEL_WORKFLOW_STATUS_PAUSED,
            failed_status=NOVEL_WORKFLOW_STATUS_FAILED,
            pending_status=NOVEL_WORKFLOW_STATUS_PENDING,
            now=datetime.now(UTC),
        )

    async def _reconcile_pause_request_if_unacknowledged(
        self,
        session: AsyncSession,
        run: NovelWorkflowRun,
    ) -> bool:
        if run.status != NOVEL_WORKFLOW_STATUS_RUNNING:
            return False
        pause_requested_at = _normalize_utc_datetime(run.pause_requested_at)
        if pause_requested_at is None:
            return False
        settings = get_settings()
        now = datetime.now(UTC)
        if now - pause_requested_at < timedelta(
            seconds=settings.analysis_pause_confirm_timeout_seconds
        ):
            return False
        last_heartbeat_at = _normalize_utc_datetime(run.last_heartbeat_at)
        if last_heartbeat_at is not None and last_heartbeat_at > pause_requested_at:
            return False
        await self.repository.mark_paused(
            session,
            run.id,
            paused_status=NOVEL_WORKFLOW_STATUS_PAUSED,
            now=now,
            stage=run.stage,
            checkpoint_kind=run.checkpoint_kind,
        )
        await session.flush()
        return True

    async def _reconcile_stale_run_if_needed(
        self,
        session: AsyncSession,
        run: NovelWorkflowRun,
    ) -> bool:
        if run.status != NOVEL_WORKFLOW_STATUS_RUNNING:
            return False
        last_activity_at = _normalize_utc_datetime(run.last_heartbeat_at or run.started_at)
        if last_activity_at is None:
            return False
        settings = get_settings()
        cutoff = datetime.now(UTC) - timedelta(seconds=settings.style_analysis_stale_timeout_seconds)
        if last_activity_at >= cutoff:
            return False
        return await self.repository.reconcile_stale_run(
            session,
            run.id,
            cutoff=cutoff,
            max_attempts=settings.style_analysis_max_attempts,
            running_status=NOVEL_WORKFLOW_STATUS_RUNNING,
            paused_status=NOVEL_WORKFLOW_STATUS_PAUSED,
            failed_status=NOVEL_WORKFLOW_STATUS_FAILED,
            pending_status=NOVEL_WORKFLOW_STATUS_PENDING,
            now=datetime.now(UTC),
        )
