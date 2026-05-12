from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


StageGetter = Callable[[], str | None]
TouchStage = Callable[[str | None], Awaitable[None]]
RunHeartbeatLoop = Callable[[StageGetter, asyncio.Event], Awaitable[None]]


@dataclass
class AnalysisWorkerJobLifecycle:
    job_id: str
    current_stage: str | None
    pause_event: asyncio.Event
    _pause_events: dict[str, asyncio.Event]
    _stop_heartbeat: asyncio.Event
    _heartbeat_task: asyncio.Task[None] | None = None

    async def update_stage(self, stage: str | None, *, touch_stage: TouchStage) -> None:
        self.current_stage = stage
        await touch_stage(stage)

    async def stop(self) -> None:
        self._stop_heartbeat.set()
        if self._heartbeat_task is not None:
            await self._heartbeat_task
        self._pause_events.pop(self.job_id, None)


def start_analysis_worker_job_lifecycle(
    *,
    job_id: str,
    initial_stage: str | None,
    pause_events: dict[str, asyncio.Event],
    run_heartbeat_loop: RunHeartbeatLoop,
) -> AnalysisWorkerJobLifecycle:
    pause_event = asyncio.Event()
    pause_events[job_id] = pause_event
    stop_heartbeat = asyncio.Event()

    lifecycle = AnalysisWorkerJobLifecycle(
        job_id=job_id,
        current_stage=initial_stage,
        pause_event=pause_event,
        _pause_events=pause_events,
        _stop_heartbeat=stop_heartbeat,
    )
    lifecycle._heartbeat_task = asyncio.create_task(
        run_heartbeat_loop(lambda: lifecycle.current_stage, stop_heartbeat)
    )
    return lifecycle


async def claim_next_pending_analysis_job(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    claim_job: Callable[[AsyncSession], Awaitable[str | None]],
) -> str | None:
    async with session_factory.begin() as session:
        return await claim_job(session)


async def recover_stale_analysis_jobs(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    recover_jobs: Callable[[AsyncSession], Awaitable[None]],
) -> None:
    async with session_factory() as session:
        await recover_jobs(session)
        await session.commit()


async def run_analysis_worker_poll_loop(
    *,
    poll_interval_seconds: float,
    max_poll_interval_seconds: float | None,
    stale_timeout_seconds: int,
    fail_stale_running_jobs: Callable[[int], Awaitable[None]],
    process_next_pending: Callable[[], Awaitable[bool]],
) -> None:
    if poll_interval_seconds <= 0:
        raise ValueError("poll_interval_seconds must be greater than 0")
    if max_poll_interval_seconds is not None and max_poll_interval_seconds <= 0:
        raise ValueError("max_poll_interval_seconds must be greater than 0")
    max_poll_interval_seconds = max_poll_interval_seconds or poll_interval_seconds
    if max_poll_interval_seconds < poll_interval_seconds:
        max_poll_interval_seconds = poll_interval_seconds

    last_stale_check = 0.0
    stale_check_interval = max(5.0, float(stale_timeout_seconds) / 3.0)
    current_interval = poll_interval_seconds
    while True:
        now = time.monotonic()
        if now - last_stale_check >= stale_check_interval:
            await fail_stale_running_jobs(stale_timeout_seconds)
            last_stale_check = now
        processed = await process_next_pending()
        if processed:
            current_interval = poll_interval_seconds
            continue
        await asyncio.sleep(current_interval)
        current_interval = min(max_poll_interval_seconds, current_interval * 2)
