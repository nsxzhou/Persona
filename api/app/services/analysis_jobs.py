from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.config import get_settings
from app.core.domain_errors import ConflictError, NotFoundError
from app.core.redaction import redact_sensitive_text


def sanitize_analysis_error_message(error_message: str | None, *, fallback: str) -> str:
    if error_message is None:
        return fallback
    normalized_message = redact_sensitive_text(error_message).strip()
    if not normalized_message:
        return fallback
    if len(normalized_message) > 200:
        return normalized_message[:199] + "…"
    return normalized_message


def reset_analysis_job_to_pending(
    job,
    *,
    target_status: str,
    reset_attempts: bool = False,
    paused_at: datetime | None = None,
) -> None:
    job.status = target_status
    job.stage = None
    job.error_message = None
    job.started_at = None
    job.completed_at = None
    job.locked_by = None
    job.locked_at = None
    job.last_heartbeat_at = None
    job.pause_requested_at = None
    job.paused_at = paused_at
    if reset_attempts:
        job.attempt_count = 0


def normalize_utc_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


async def reconcile_unacknowledged_pause_request(
    session,
    job,
    *,
    repository,
    running_status: str,
    paused_status: str,
    pause_confirm_timeout_seconds: int,
) -> bool:
    if job.status != running_status:
        return False
    pause_requested_at = normalize_utc_datetime(job.pause_requested_at)
    if pause_requested_at is None:
        return False
    now = datetime.now(UTC)
    if now - pause_requested_at < timedelta(seconds=pause_confirm_timeout_seconds):
        return False
    last_heartbeat_at = normalize_utc_datetime(job.last_heartbeat_at)
    if last_heartbeat_at is not None and last_heartbeat_at > pause_requested_at:
        return False
    await repository.mark_paused(
        session,
        job.id,
        paused_status=paused_status,
        now=now,
        stage=job.stage,
    )
    await session.flush()
    return True


async def reconcile_stale_running_job(
    session,
    job,
    *,
    repository,
    stale_timeout_seconds: int,
    max_attempts: int,
    running_status: str,
    paused_status: str,
    failed_status: str,
    pending_status: str,
) -> bool:
    if job.status != running_status:
        return False
    last_activity_at = normalize_utc_datetime(job.last_heartbeat_at or job.started_at)
    if last_activity_at is None:
        return False
    now = datetime.now(UTC)
    cutoff = now - timedelta(seconds=stale_timeout_seconds)
    if last_activity_at >= cutoff:
        return False
    reconciled = await repository.reconcile_stale_job(
        session,
        job.id,
        cutoff=cutoff,
        max_attempts=max_attempts,
        running_status=running_status,
        paused_status=paused_status,
        failed_status=failed_status,
        pending_status=pending_status,
        now=now,
    )
    if reconciled:
        await session.flush()
    return reconciled


def resolve_analysis_payload_result_or_409(
    result,
    *,
    job_id: str,
    succeeded_status: str,
    parser: Callable[[Any], Any],
    not_ready_detail: str,
):
    if result is None:
        raise NotFoundError(f"分析任务不存在: job_id={job_id}")
    job_status, payload = result
    if job_status != succeeded_status or payload is None:
        raise ConflictError(not_ready_detail)
    return parser(payload)


def mark_analysis_job_failed(
    job,
    *,
    pending_status: str,
    failed_status: str,
    error_message: str,
    max_attempts: int,
    sanitize_error_message: Callable[[str | None], str],
) -> bool:
    retryable = job.attempt_count < max_attempts
    job.status = pending_status if retryable else failed_status
    job.stage = None
    job.error_message = None if retryable else sanitize_error_message(error_message)
    job.started_at = None if retryable else job.started_at
    job.completed_at = None if retryable else datetime.now(UTC)
    job.locked_by = None
    job.locked_at = None
    job.last_heartbeat_at = None
    return not retryable


class BaseAnalysisJobService:
    repository: Any
    storage_service: Any
    job_not_found_message = "分析任务不存在: job_id={job_id}"
    status_response_type: Any
    preparing_stage: str
    pending_status: str
    running_status: str
    paused_status: str
    failed_status: str
    succeeded_status: str
    stale_timeout_setting_name: str
    max_attempts_setting_name: str
    sanitize_error_message: Callable[[str | None], str]

    async def list(
        self,
        session,
        *,
        user_id: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Any]:
        limit = min(max(limit, 1), 100)
        return await self.repository.list(
            session,
            user_id=user_id,
            offset=offset,
            limit=limit,
            include_payloads=False,
        )

    async def get_or_404(
        self,
        session,
        job_id: str,
        *,
        user_id: str | None = None,
        include_payloads: bool = True,
    ):
        job = await self.repository.get_by_id(
            session,
            job_id,
            user_id=user_id,
            include_payloads=include_payloads,
        )
        if job is None:
            raise NotFoundError(self.job_not_found_message.format(job_id=job_id))
        return job

    async def get_status_or_404(
        self,
        session,
        job_id: str,
        *,
        user_id: str | None = None,
    ):
        job = await self.get_or_404(
            session,
            job_id,
            user_id=user_id,
            include_payloads=False,
        )
        if await self._reconcile_pause_request_if_unacknowledged(session, job):
            job = await self.get_or_404(
                session,
                job_id,
                user_id=user_id,
                include_payloads=False,
            )
        if await self._reconcile_stale_job_if_needed(session, job):
            job = await self.get_or_404(
                session,
                job_id,
                user_id=user_id,
                include_payloads=False,
            )
        return self.status_response_type(
            id=job.id,
            status=job.status,
            stage=job.stage,
            error_message=job.error_message,
            updated_at=job.updated_at,
            pause_requested_at=job.pause_requested_at,
        )

    async def get_job_logs_or_404(
        self,
        session,
        job_id: str,
        *,
        user_id: str | None = None,
        offset: int = 0,
    ):
        await self.get_or_404(
            session,
            job_id,
            user_id=user_id,
            include_payloads=False,
        )
        content, next_offset, truncated = await self.storage_service.read_job_logs_incremental(
            job_id,
            offset=offset,
        )
        return self.job_logs_response_type(
            content=content,
            next_offset=next_offset,
            truncated=truncated,
        )

    async def resume(
        self,
        session,
        job_id: str,
        *,
        user_id: str | None = None,
    ):
        job = await self.get_or_404(
            session,
            job_id,
            user_id=user_id,
            include_payloads=False,
        )
        if job.status == self.running_status and job.locked_by:
            raise ConflictError("分析任务正在运行，无法恢复")
        if job.status == self.succeeded_status:
            raise ConflictError("分析任务已成功完成，无需恢复")
        if job.status == self.paused_status:
            reset_analysis_job_to_pending(job, target_status=self.pending_status)
            await session.flush()
            return await self.get_status_or_404(session, job_id, user_id=user_id)
        reset_analysis_job_to_pending(
            job,
            target_status=self.pending_status,
            reset_attempts=True,
        )
        await session.flush()
        return await self.get_status_or_404(session, job_id, user_id=user_id)

    async def pause(
        self,
        session,
        job_id: str,
        *,
        user_id: str | None = None,
    ):
        job = await self.get_or_404(
            session,
            job_id,
            user_id=user_id,
            include_payloads=False,
        )
        if job.status == self.succeeded_status:
            raise ConflictError("分析任务已成功完成，无法暂停")
        if job.status == self.failed_status:
            raise ConflictError("分析任务已失败，无法暂停")
        if job.status == self.paused_status:
            return await self.get_status_or_404(session, job_id, user_id=user_id)
        if job.status == self.pending_status:
            reset_analysis_job_to_pending(
                job,
                target_status=self.paused_status,
                paused_at=datetime.now(UTC),
            )
            await session.flush()
            return await self.get_status_or_404(session, job_id, user_id=user_id)
        await self.repository.request_pause(
            session,
            job_id,
            running_status=self.running_status,
            now=datetime.now(UTC),
        )
        await session.flush()
        refreshed = await self.get_or_404(
            session,
            job_id,
            user_id=user_id,
            include_payloads=False,
        )
        await self._reconcile_pause_request_if_unacknowledged(session, refreshed)
        await self._reconcile_stale_job_if_needed(session, refreshed)
        return await self.get_status_or_404(session, job_id, user_id=user_id)

    async def _reconcile_pause_request_if_unacknowledged(self, session, job) -> bool:
        settings = get_settings()
        return await reconcile_unacknowledged_pause_request(
            session,
            job,
            repository=self.repository,
            running_status=self.running_status,
            paused_status=self.paused_status,
            pause_confirm_timeout_seconds=settings.analysis_pause_confirm_timeout_seconds,
        )

    async def _reconcile_stale_job_if_needed(self, session, job) -> bool:
        settings = get_settings()
        return await reconcile_stale_running_job(
            session,
            job,
            repository=self.repository,
            stale_timeout_seconds=getattr(settings, self.stale_timeout_setting_name),
            max_attempts=getattr(settings, self.max_attempts_setting_name),
            running_status=self.running_status,
            paused_status=self.paused_status,
            failed_status=self.failed_status,
            pending_status=self.pending_status,
        )

    async def claim_job_for_worker(
        self,
        session,
        *,
        worker_id: str,
        max_attempts: int,
    ) -> str | None:
        return await self.repository.claim_pending_job(
            session,
            worker_id=worker_id,
            max_attempts=max_attempts,
            preparing_stage=self.preparing_stage,
            running_status=self.running_status,
            pending_status=self.pending_status,
            now=datetime.now(UTC),
        )

    async def heartbeat_job(
        self,
        session,
        job_id: str,
        *,
        stage: str | None,
        checkpoint_kind: str | None = None,
    ) -> datetime | None:
        del checkpoint_kind
        return await self.repository.heartbeat(
            session,
            job_id,
            running_status=self.running_status,
            stage=stage,
            now=datetime.now(UTC),
        )

    async def mark_job_paused(
        self,
        session,
        job_id: str,
        *,
        stage: str | None,
        checkpoint_kind: str | None = None,
    ) -> None:
        del checkpoint_kind
        await self.repository.mark_paused(
            session,
            job_id,
            paused_status=self.paused_status,
            now=datetime.now(UTC),
            stage=stage,
        )

    async def mark_job_failed(
        self,
        session,
        job_id: str,
        *,
        error_message: str,
        max_attempts: int,
        force_terminal: bool = False,
    ) -> bool:
        del force_terminal
        job = await self.get_or_404(session, job_id)
        return mark_analysis_job_failed(
            job,
            pending_status=self.pending_status,
            failed_status=self.failed_status,
            error_message=error_message,
            max_attempts=max_attempts,
            sanitize_error_message=self.sanitize_error_message,
        )

    async def recover_stale_jobs(
        self,
        session,
        *,
        stale_after_seconds: int,
        max_attempts: int,
    ) -> None:
        await self.repository.recover_stale_jobs(
            session,
            cutoff=datetime.now(UTC) - timedelta(seconds=stale_after_seconds),
            max_attempts=max_attempts,
            running_status=self.running_status,
            paused_status=self.paused_status,
            failed_status=self.failed_status,
            pending_status=self.pending_status,
            now=datetime.now(UTC),
        )


async def cleanup_analysis_job_external_resources(
    *,
    job_id: str,
    sample_storage_path: str | None,
    storage_service,
    checkpointer_factory,
    logger: logging.Logger,
    sample_delete_error_message: str,
    artifact_cleanup_error_message: str,
    checkpoint_cleanup_error_message: str,
) -> None:
    try:
        if sample_storage_path:
            await storage_service.delete_sample_file(sample_storage_path)
    except OSError:
        logger.exception(sample_delete_error_message, extra={"job_id": job_id})

    try:
        await storage_service.cleanup_job_artifacts(job_id)
    except OSError:
        logger.exception(artifact_cleanup_error_message, extra={"job_id": job_id})

    try:
        await checkpointer_factory.delete_thread(job_id)
    except Exception:
        # Checkpointer backends can raise driver-specific errors; deletion is
        # best-effort after the DB row is gone, so do not fail user deletion.
        logger.exception(checkpoint_cleanup_error_message, extra={"job_id": job_id})


def get_analysis_heartbeat_interval_seconds(stale_timeout_seconds: int | float) -> float:
    safe_timeout_seconds = max(1.0, float(stale_timeout_seconds))
    return max(0.2, min(30.0, safe_timeout_seconds / 3))


async def run_analysis_stage_heartbeat_loop(
    *,
    job_id: str,
    get_stage: Callable[[], str | None],
    get_checkpoint_kind: Callable[[], str | None] | None = None,
    stop_event: asyncio.Event,
    interval_seconds: float,
    touch_stage: Callable[[str | None, str | None], Awaitable[None]],
    logger: logging.Logger,
    failure_log_message: str,
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
                checkpoint_kind = get_checkpoint_kind() if get_checkpoint_kind is not None else None
                await touch_stage(stage, checkpoint_kind)
            except Exception:
                # Heartbeat failures are logged and retried by the next loop;
                # the worker execution path owns terminal job failure semantics.
                logger.exception(
                    failure_log_message,
                    extra={"job_id": job_id, "stage": stage},
                )
