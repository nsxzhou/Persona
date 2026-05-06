from __future__ import annotations

from datetime import UTC, datetime

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
