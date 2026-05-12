from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from types import TracebackType

import pytest

from app.services.analysis_worker_lifecycle import (
    BaseAnalysisJobExecutor,
    ShouldPause,
    StageCallback,
)


class _AsyncContext:
    def __init__(self, session: object) -> None:
        self.session = session

    async def __aenter__(self) -> object:
        return self.session

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


class _Session:
    def __init__(self) -> None:
        self.commit_count = 0

    async def commit(self) -> None:
        self.commit_count += 1


class _SessionFactory:
    def __init__(self) -> None:
        self.sessions: list[_Session] = []

    def __call__(self) -> _AsyncContext:
        session = _Session()
        self.sessions.append(session)
        return _AsyncContext(session)

    def begin(self) -> _AsyncContext:
        session = _Session()
        self.sessions.append(session)
        return _AsyncContext(session)


class _JobService:
    def __init__(self, claim_id: str | None = "job-1") -> None:
        self.claim_id = claim_id
        self.claim_worker_id: str | None = None
        self.claim_max_attempts: int | None = None
        self.heartbeat_stages: list[str | None] = []
        self.failed: list[tuple[str, str, int]] = []
        self.paused: list[tuple[str, str | None]] = []
        self.recovered: list[tuple[int, int]] = []

    async def claim_job_for_worker(
        self,
        session: object,
        *,
        worker_id: str,
        max_attempts: int,
    ) -> str | None:
        self.claim_worker_id = worker_id
        self.claim_max_attempts = max_attempts
        return self.claim_id

    async def heartbeat_job(
        self,
        session: object,
        job_id: str,
        *,
        stage: str | None,
    ) -> datetime | None:
        self.heartbeat_stages.append(stage)
        return None

    async def mark_job_failed(
        self,
        session: object,
        job_id: str,
        *,
        error_message: str,
        max_attempts: int,
    ) -> bool:
        self.failed.append((job_id, error_message, max_attempts))
        return True

    async def mark_job_paused(
        self,
        session: object,
        job_id: str,
        *,
        stage: str | None,
    ) -> None:
        self.paused.append((job_id, stage))

    async def recover_stale_jobs(
        self,
        session: object,
        *,
        stale_after_seconds: int,
        max_attempts: int,
    ) -> None:
        self.recovered.append((stale_after_seconds, max_attempts))


class _StorageService:
    def __init__(self) -> None:
        self.cleaned: list[str] = []

    async def cleanup_job_artifacts(self, job_id: str) -> None:
        self.cleaned.append(job_id)


class _CheckpointerFactory:
    def __init__(self) -> None:
        self.closed = False
        self.deleted_threads: list[str] = []

    async def aclose(self) -> None:
        self.closed = True

    async def delete_thread(self, thread_id: str) -> None:
        self.deleted_threads.append(thread_id)


class _PauseRequested(Exception):
    pass


class _Executor(BaseAnalysisJobExecutor):
    initial_stage = "preparing"
    pause_exceptions = (_PauseRequested,)
    failure_log_message = "analysis job failed"
    heartbeat_failure_log_message = "analysis heartbeat failed"
    logger = logging.getLogger(__name__)

    def __init__(
        self,
        *,
        job_service: _JobService,
        storage_service: _StorageService,
        checkpointer_factory: _CheckpointerFactory,
        run_job: Callable[[StageCallback, ShouldPause], Awaitable[None]],
    ) -> None:
        super().__init__(
            job_service=job_service,
            storage_service=storage_service,
            checkpointer_factory=checkpointer_factory,
            worker_id_prefix="test-worker",
        )
        self._run_job = run_job

    def _max_attempts(self) -> int:
        return 3

    def _stale_timeout_seconds(self) -> int:
        return 30

    async def _run_job_to_success(
        self,
        session_factory: object,
        job_id: str,
        *,
        stage_callback: StageCallback,
        should_pause: ShouldPause,
    ) -> None:
        await self._run_job(stage_callback, should_pause)


@pytest.mark.asyncio
async def test_base_analysis_executor_claims_runs_and_cleans_successful_job() -> None:
    job_service = _JobService()
    storage_service = _StorageService()
    checkpointer_factory = _CheckpointerFactory()

    async def run_job(stage_callback: StageCallback, should_pause: ShouldPause) -> None:
        assert should_pause() is False
        await stage_callback("running")

    executor = _Executor(
        job_service=job_service,
        storage_service=storage_service,
        checkpointer_factory=checkpointer_factory,
        run_job=run_job,
    )
    session_factory = _SessionFactory()

    assert await executor.process_next_pending(session_factory) is True

    assert job_service.claim_worker_id is not None
    assert job_service.claim_worker_id.startswith("test-worker-")
    assert job_service.claim_max_attempts == 3
    assert job_service.heartbeat_stages == ["running"]
    assert job_service.failed == []
    assert job_service.paused == []
    assert storage_service.cleaned == ["job-1"]
    assert checkpointer_factory.deleted_threads == ["job-1"]


@pytest.mark.asyncio
async def test_base_analysis_executor_marks_failed_without_success_cleanup() -> None:
    job_service = _JobService()
    storage_service = _StorageService()
    checkpointer_factory = _CheckpointerFactory()

    async def run_job(stage_callback: StageCallback, should_pause: ShouldPause) -> None:
        await stage_callback("running")
        raise RuntimeError("boom")

    executor = _Executor(
        job_service=job_service,
        storage_service=storage_service,
        checkpointer_factory=checkpointer_factory,
        run_job=run_job,
    )

    assert await executor.process_next_pending(_SessionFactory()) is True

    assert job_service.failed == [("job-1", "boom", 3)]
    assert job_service.paused == []
    assert storage_service.cleaned == []
    assert checkpointer_factory.deleted_threads == []


@pytest.mark.asyncio
async def test_base_analysis_executor_marks_pause_with_current_stage() -> None:
    job_service = _JobService()
    storage_service = _StorageService()
    checkpointer_factory = _CheckpointerFactory()

    async def run_job(stage_callback: StageCallback, should_pause: ShouldPause) -> None:
        await stage_callback("chunking")
        raise _PauseRequested

    executor = _Executor(
        job_service=job_service,
        storage_service=storage_service,
        checkpointer_factory=checkpointer_factory,
        run_job=run_job,
    )

    assert await executor.process_next_pending(_SessionFactory()) is True

    assert job_service.failed == []
    assert job_service.paused == [("job-1", "chunking")]
    assert storage_service.cleaned == []
    assert checkpointer_factory.deleted_threads == []


@pytest.mark.asyncio
async def test_base_analysis_executor_recovers_stale_jobs_with_retry_limit() -> None:
    job_service = _JobService(claim_id=None)
    storage_service = _StorageService()
    checkpointer_factory = _CheckpointerFactory()

    async def run_job(stage_callback: StageCallback, should_pause: ShouldPause) -> None:
        raise AssertionError("no job should run")

    executor = _Executor(
        job_service=job_service,
        storage_service=storage_service,
        checkpointer_factory=checkpointer_factory,
        run_job=run_job,
    )
    session_factory = _SessionFactory()

    assert await executor.process_next_pending(session_factory) is False
    await executor.fail_stale_running_jobs(session_factory, stale_after_seconds=45)

    assert job_service.recovered == [(45, 3)]
