from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

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
    succeeded_status: str,
    parser: Callable[[Any], Any],
    not_ready_detail: str,
):
    if result is None:
        raise NotFoundError("分析任务不存在")
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
        logger.exception(checkpoint_cleanup_error_message, extra={"job_id": job_id})


def get_analysis_heartbeat_interval_seconds(stale_timeout_seconds: int | float) -> float:
    safe_timeout_seconds = max(1.0, float(stale_timeout_seconds))
    return max(0.2, min(30.0, safe_timeout_seconds / 3))


async def run_analysis_stage_heartbeat_loop(
    *,
    job_id: str,
    get_stage: Callable[[], str | None],
    stop_event: asyncio.Event,
    interval_seconds: float,
    touch_stage: Callable[[str | None], Awaitable[None]],
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
                await touch_stage(stage)
            except Exception:
                logger.exception(
                    failure_log_message,
                    extra={"job_id": job_id, "stage": stage},
                )
