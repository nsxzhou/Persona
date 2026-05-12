from __future__ import annotations

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.services.analysis_jobs import (
    get_analysis_heartbeat_interval_seconds,
    run_analysis_stage_heartbeat_loop,
)


StageGetter = Callable[[], str | None]
TouchStage = Callable[[str | None], Awaitable[None]]
RunHeartbeatLoop = Callable[[StageGetter, asyncio.Event], Awaitable[None]]
StageCallback = Callable[[str | None], Awaitable[None]]
ShouldPause = Callable[[], bool]


class AnalysisWorkerJobService(Protocol):
    async def claim_job_for_worker(
        self,
        session: AsyncSession,
        *,
        worker_id: str,
        max_attempts: int,
    ) -> str | None: ...

    async def heartbeat_job(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        stage: str | None,
    ) -> datetime | None: ...

    async def mark_job_failed(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        error_message: str,
        max_attempts: int,
    ) -> bool: ...

    async def mark_job_paused(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        stage: str | None,
    ) -> None: ...

    async def recover_stale_jobs(
        self,
        session: AsyncSession,
        *,
        stale_after_seconds: int,
        max_attempts: int,
    ) -> None: ...


class AnalysisWorkerStorageService(Protocol):
    async def cleanup_job_artifacts(self, job_id: str) -> None: ...


class AnalysisWorkerCheckpointerFactory(Protocol):
    async def aclose(self) -> None: ...

    async def delete_thread(self, thread_id: str) -> None: ...


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


class BaseAnalysisJobExecutor(ABC):
    initial_stage: ClassVar[str | None]
    pause_exceptions: ClassVar[tuple[type[BaseException], ...]]
    failure_log_message: ClassVar[str]
    heartbeat_failure_log_message: ClassVar[str]
    logger: ClassVar[logging.Logger]

    def __init__(
        self,
        *,
        job_service: AnalysisWorkerJobService,
        checkpointer_factory: AnalysisWorkerCheckpointerFactory,
        storage_service: AnalysisWorkerStorageService,
        worker_id_prefix: str,
    ) -> None:
        self.job_service = job_service
        self.checkpointer_factory = checkpointer_factory
        self.storage_service = storage_service
        self._pause_events: dict[str, asyncio.Event] = {}
        self._worker_id = f"{worker_id_prefix}-{uuid.uuid4()}"
        self._logger = self.logger

    async def aclose(self) -> None:
        await self.checkpointer_factory.aclose()

    async def process_next_pending(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> bool:
        job_id = await self._claim_next_pending_job(
            session_factory,
            worker_id=self._worker_id,
        )
        if job_id is None:
            return False

        await self._run_claimed_job(session_factory, job_id)
        return True

    async def _claim_next_pending_job(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        worker_id: str,
    ) -> str | None:
        return await claim_next_pending_analysis_job(
            session_factory,
            claim_job=lambda session: self.job_service.claim_job_for_worker(
                session,
                worker_id=worker_id,
                max_attempts=self._max_attempts(),
            ),
        )

    async def _run_claimed_job(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
    ) -> None:
        should_cleanup = False
        lifecycle = start_analysis_worker_job_lifecycle(
            job_id=job_id,
            initial_stage=self.initial_stage,
            pause_events=self._pause_events,
            run_heartbeat_loop=lambda get_stage, stop_event: self._run_stage_heartbeat_loop(
                session_factory,
                job_id,
                get_stage=get_stage,
                stop_event=stop_event,
                interval_seconds=self._heartbeat_interval_seconds(),
            ),
        )

        async def stage_callback(stage: str | None) -> None:
            await lifecycle.update_stage(
                stage,
                touch_stage=lambda next_stage: self._touch_job_stage(
                    session_factory,
                    job_id,
                    stage=next_stage,
                ),
            )

        try:
            await self._run_job_to_success(
                session_factory,
                job_id,
                stage_callback=stage_callback,
                should_pause=lifecycle.pause_event.is_set,
            )
            should_cleanup = True
        except self.pause_exceptions:
            await self._mark_job_paused(
                session_factory,
                job_id,
                stage=lifecycle.current_stage,
            )
        except Exception as exc:
            self._logger.exception(
                self.failure_log_message,
                extra={"job_id": job_id},
            )
            await self._mark_job_failed(
                session_factory,
                job_id,
                error_message=str(exc),
            )
        finally:
            await lifecycle.stop()
            if should_cleanup:
                await self.storage_service.cleanup_job_artifacts(job_id)
                await self._delete_checkpointer_thread(job_id)

    def _heartbeat_interval_seconds(self) -> float:
        return get_analysis_heartbeat_interval_seconds(self._stale_timeout_seconds())

    async def _run_stage_heartbeat_loop(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
        *,
        get_stage: Callable[[], str | None],
        stop_event: asyncio.Event,
        interval_seconds: float,
    ) -> None:
        await run_analysis_stage_heartbeat_loop(
            job_id=job_id,
            get_stage=get_stage,
            stop_event=stop_event,
            interval_seconds=interval_seconds,
            touch_stage=lambda stage: self._touch_job_stage(
                session_factory,
                job_id,
                stage=stage,
            ),
            logger=self._logger,
            failure_log_message=self.heartbeat_failure_log_message,
        )

    async def _touch_job_stage(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
        *,
        stage: str | None,
    ) -> None:
        async with session_factory() as session:
            pause_requested_at = await self.job_service.heartbeat_job(
                session, job_id, stage=stage
            )
            await session.commit()
            if pause_requested_at is not None:
                pause_event = self._pause_events.get(job_id)
                if pause_event is not None:
                    pause_event.set()

    async def _mark_job_failed(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
        *,
        error_message: str,
    ) -> bool:
        async with session_factory() as session:
            is_terminal = await self.job_service.mark_job_failed(
                session,
                job_id,
                error_message=error_message,
                max_attempts=self._max_attempts(),
            )
            await session.commit()
            return is_terminal

    async def _mark_job_paused(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
        *,
        stage: str | None,
    ) -> None:
        async with session_factory() as session:
            await self.job_service.mark_job_paused(session, job_id, stage=stage)
            await session.commit()

    async def _delete_checkpointer_thread(self, job_id: str) -> None:
        await self.checkpointer_factory.delete_thread(job_id)

    async def fail_stale_running_jobs(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        stale_after_seconds: int,
    ) -> None:
        await recover_stale_analysis_jobs(
            session_factory,
            recover_jobs=lambda session: self.job_service.recover_stale_jobs(
                session,
                stale_after_seconds=stale_after_seconds,
                max_attempts=self._max_attempts(),
            ),
        )

    async def run_worker(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        poll_interval_seconds: float,
        max_poll_interval_seconds: float | None = None,
    ) -> None:
        await run_analysis_worker_poll_loop(
            poll_interval_seconds=poll_interval_seconds,
            max_poll_interval_seconds=max_poll_interval_seconds,
            stale_timeout_seconds=self._stale_timeout_seconds(),
            fail_stale_running_jobs=lambda stale_after_seconds: self.fail_stale_running_jobs(
                session_factory,
                stale_after_seconds=stale_after_seconds,
            ),
            process_next_pending=lambda: self.process_next_pending(session_factory),
        )

    @abstractmethod
    def _max_attempts(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def _stale_timeout_seconds(self) -> int:
        raise NotImplementedError

    @abstractmethod
    async def _run_job_to_success(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
        *,
        stage_callback: StageCallback,
        should_pause: ShouldPause,
    ) -> None:
        raise NotImplementedError
