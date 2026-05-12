from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain_errors import NotFoundError
from app.db.repositories.novel_workflows import NovelWorkflowRepository
from app.schemas.novel_workflows import (
    NOVEL_WORKFLOW_STAGE_PREPARING,
    NOVEL_WORKFLOW_STATUS_FAILED,
    NOVEL_WORKFLOW_STATUS_PAUSED,
    NOVEL_WORKFLOW_STATUS_PENDING,
    NOVEL_WORKFLOW_STATUS_RUNNING,
    NOVEL_WORKFLOW_STATUS_SUCCEEDED,
)


def reset_run_to_pending(
    run,
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


class NovelWorkflowLifecycleService:
    def __init__(self, repository: NovelWorkflowRepository | None = None) -> None:
        self.repository = repository or NovelWorkflowRepository()

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

    async def claim_job_by_id_for_worker(
        self,
        session: AsyncSession,
        run_id: str,
        *,
        worker_id: str,
    ) -> bool:
        return await self.repository.claim_pending_run_by_id(
            session,
            run_id,
            worker_id=worker_id,
            preparing_stage=NOVEL_WORKFLOW_STAGE_PREPARING,
            running_status=NOVEL_WORKFLOW_STATUS_RUNNING,
            pending_status=NOVEL_WORKFLOW_STATUS_PENDING,
            now=datetime.now(UTC),
        )

    async def heartbeat_job(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        stage: str | None,
        checkpoint_kind: str | None = None,
    ) -> datetime | None:
        return await self.heartbeat_run(
            session,
            job_id,
            stage=stage,
            checkpoint_kind=checkpoint_kind,
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

    async def mark_job_paused(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        stage: str | None,
        checkpoint_kind: str | None = None,
    ) -> None:
        await self.mark_run_paused(
            session,
            job_id,
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
            raise NotFoundError(f"工作流任务不存在: run_id={run_id}")
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
        force_terminal: bool = False,
    ) -> bool:
        run = await self.repository.get_by_id(session, run_id)
        if run is None:
            raise NotFoundError(f"工作流任务不存在: run_id={run_id}")
        is_terminal = force_terminal or run.attempt_count >= max_attempts
        if is_terminal:
            run.status = NOVEL_WORKFLOW_STATUS_FAILED
            run.error_message = error_message
            run.stage = None
            run.checkpoint_kind = None
            run.completed_at = datetime.now(UTC)
        else:
            reset_run_to_pending(run)
            run.error_message = error_message
        await session.flush()
        return is_terminal

    async def mark_job_failed(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        error_message: str,
        max_attempts: int,
        force_terminal: bool = False,
    ) -> bool:
        return await self.mark_run_failed(
            session,
            job_id,
            error_message=error_message,
            max_attempts=max_attempts,
            force_terminal=force_terminal,
        )

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

    async def recover_stale_jobs(
        self,
        session: AsyncSession,
        *,
        stale_after_seconds: int,
        max_attempts: int,
    ) -> None:
        await self.recover_stale_runs(
            session,
            stale_after_seconds=stale_after_seconds,
            max_attempts=max_attempts,
        )
