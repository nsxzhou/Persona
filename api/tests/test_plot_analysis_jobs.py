from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select

from app.db.models import PlotAnalysisJob
from app.services.plot_analysis_jobs import PlotAnalysisJobService
from app.services.plot_analysis_worker import PlotAnalysisWorkerService


def test_plot_analysis_job_service_supports_dependency_injection() -> None:
    from app.services.plot_analysis_checkpointer import PlotAnalysisCheckpointerFactory
    from app.services.plot_analysis_jobs import PlotAnalysisJobService
    from app.services.plot_analysis_storage import PlotAnalysisStorageService
    from app.services.provider_configs import ProviderConfigService

    provider_service = ProviderConfigService()
    storage_service = PlotAnalysisStorageService()
    checkpointer_factory = PlotAnalysisCheckpointerFactory()

    service = PlotAnalysisJobService(
        provider_service=provider_service,
        storage_service=storage_service,
        checkpointer_factory=checkpointer_factory,
    )

    assert service.provider_service is provider_service
    assert service.storage_service is storage_service
    assert service.checkpointer_factory is checkpointer_factory


@pytest.mark.asyncio
async def test_plot_worker_uses_configured_chunk_concurrency(
    initialized_client: AsyncClient,
    app_with_db: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STYLE_ANALYSIS_CHUNK_MAX_CONCURRENCY", "5")
    from app.core.config import get_settings

    get_settings.cache_clear()
    provider_id = (await initialized_client.get("/api/v1/provider-configs")).json()[0]["id"]
    create_response = await initialized_client.post(
        "/api/v1/plot-analysis-jobs",
        data={"plot_name": "并发限制测试", "provider_id": provider_id},
        files={"file": ("sample.txt", "第一段。\n\n第二段。\n\n第三段。".encode("utf-8"), "text/plain")},
    )
    assert create_response.status_code == 201

    service = PlotAnalysisWorkerService()
    observed: dict[str, int] = {}

    async def fake_load_run_context(session_factory, job_id: str):
        del session_factory, job_id
        return SimpleNamespace(
            provider=SimpleNamespace(),
            plot_name="并发限制测试",
            model_name="gpt-4.1-mini",
            source_filename="sample.txt",
            chunk_count=3,
            classification={
                "text_type": "章节正文",
                "has_timestamps": False,
                "has_speaker_labels": False,
                "has_noise_markers": False,
                "uses_batch_processing": True,
                "location_indexing": "章节或段落位置",
            },
        )

    async def fake_build_pipeline(
        *,
        provider,
        model_name: str,
        plot_name: str,
        source_filename: str,
        stage_callback,
        should_pause=None,
    ):
        del provider, model_name, plot_name, source_filename, stage_callback, should_pause

        class FakePipeline:
            async def run(
                self,
                *,
                job_id: str,
                chunk_count: int,
                classification: dict,
                max_concurrency: int,
            ):
                del job_id, chunk_count, classification
                observed["max_concurrency"] = max_concurrency
                raise RuntimeError("stop after capture")

        return FakePipeline()

    async def fake_mark_job_failed(session_factory, job_id: str, *, error_message: str):
        del session_factory, job_id, error_message
        return True

    monkeypatch.setattr(service, "_load_run_context", fake_load_run_context)
    monkeypatch.setattr(service, "_build_pipeline", fake_build_pipeline)
    monkeypatch.setattr(service, "_mark_job_failed", fake_mark_job_failed)

    processed = await service.process_next_pending(app_with_db.state.session_factory)
    assert processed is True
    assert observed["max_concurrency"] == 5

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_default_worker_entrypoint_also_starts_plot_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.worker as worker_module

    calls: dict[str, object] = {}

    class FakeEngine:
        def __init__(self) -> None:
            self.dispose_calls = 0

        async def dispose(self) -> None:
            self.dispose_calls += 1

    class FakeStyleService:
        def __init__(self) -> None:
            self.aclose_calls = 0

        async def run_worker(
            self,
            session_factory,
            *,
            poll_interval_seconds: float,
            max_poll_interval_seconds: float | None = None,
        ) -> None:
            calls["style"] = {
                "session_factory": session_factory,
                "poll_interval_seconds": poll_interval_seconds,
                "max_poll_interval_seconds": max_poll_interval_seconds,
            }

        async def aclose(self) -> None:
            self.aclose_calls += 1

    class FakePlotService:
        def __init__(self) -> None:
            self.aclose_calls = 0

        async def run_worker(
            self,
            session_factory,
            *,
            poll_interval_seconds: float,
            max_poll_interval_seconds: float | None = None,
        ) -> None:
            calls["plot"] = {
                "session_factory": session_factory,
                "poll_interval_seconds": poll_interval_seconds,
                "max_poll_interval_seconds": max_poll_interval_seconds,
            }

        async def aclose(self) -> None:
            self.aclose_calls += 1

    fake_engine = FakeEngine()
    fake_session_factory = object()
    fake_style_service = FakeStyleService()
    fake_plot_service = FakePlotService()
    settings = SimpleNamespace(
        style_analysis_worker_enabled=True,
        database_url="sqlite+aiosqlite:///./test.db",
        style_analysis_poll_interval_seconds=1.5,
        style_analysis_stale_timeout_seconds=30,
    )

    monkeypatch.setattr(worker_module, "get_settings", lambda: settings)
    monkeypatch.setattr(worker_module, "create_engine", lambda database_url: fake_engine)
    monkeypatch.setattr(worker_module, "create_session_factory", lambda engine: fake_session_factory)
    monkeypatch.setattr(worker_module, "StyleAnalysisWorkerService", lambda: fake_style_service)
    monkeypatch.setattr(worker_module, "PlotAnalysisWorkerService", lambda: fake_plot_service)

    await worker_module.run_worker()

    assert calls == {
        "style": {
            "session_factory": fake_session_factory,
            "poll_interval_seconds": 1.5,
            "max_poll_interval_seconds": 6.0,
        },
        "plot": {
            "session_factory": fake_session_factory,
            "poll_interval_seconds": 1.5,
            "max_poll_interval_seconds": 6.0,
        },
    }
    assert fake_style_service.aclose_calls == 1
    assert fake_plot_service.aclose_calls == 1
    assert fake_engine.dispose_calls == 1


@pytest.mark.asyncio
async def test_pause_running_stale_plot_job_transitions_to_paused_immediately(
    initialized_client: AsyncClient,
    app_with_db: FastAPI,
) -> None:
    provider_id = (await initialized_client.get("/api/v1/provider-configs")).json()[0]["id"]
    create_response = await initialized_client.post(
        "/api/v1/plot-analysis-jobs",
        data={"plot_name": "陈旧运行中暂停", "provider_id": provider_id},
        files={"file": ("sample.txt", "第一段。".encode("utf-8"), "text/plain")},
    )
    job_id = create_response.json()["id"]

    stale_at = datetime.now(UTC) - timedelta(minutes=10)
    async with app_with_db.state.session_factory() as session:
        job = await PlotAnalysisJobService().get_or_404(session, job_id)
        job.status = "running"
        job.stage = "analyzing_focus_chunks"
        job.locked_by = "dead-worker"
        job.locked_at = stale_at
        job.last_heartbeat_at = stale_at
        job.attempt_count = 1
        await session.commit()

    pause_response = await initialized_client.post(f"/api/v1/plot-analysis-jobs/{job_id}/pause")
    assert pause_response.status_code == 200
    assert pause_response.json()["status"] == "paused"
    assert pause_response.json()["pause_requested_at"] is None

    async with app_with_db.state.session_factory() as session:
        job = await session.scalar(select(PlotAnalysisJob).where(PlotAnalysisJob.id == job_id))
        assert job is not None
        assert job.status == "paused"
        assert job.pause_requested_at is None
        assert job.locked_by is None
        assert job.last_heartbeat_at is None


@pytest.mark.asyncio
async def test_get_plot_status_reconciles_stale_running_job_back_to_pending(
    initialized_client: AsyncClient,
    app_with_db: FastAPI,
) -> None:
    provider_id = (await initialized_client.get("/api/v1/provider-configs")).json()[0]["id"]
    create_response = await initialized_client.post(
        "/api/v1/plot-analysis-jobs",
        data={"plot_name": "陈旧运行中", "provider_id": provider_id},
        files={"file": ("sample.txt", "第一段。".encode("utf-8"), "text/plain")},
    )
    job_id = create_response.json()["id"]

    stale_at = datetime.now(UTC) - timedelta(minutes=10)
    async with app_with_db.state.session_factory() as session:
        job = await PlotAnalysisJobService().get_or_404(session, job_id)
        job.status = "running"
        job.stage = "analyzing_focus_chunks"
        job.locked_by = "dead-worker"
        job.locked_at = stale_at
        job.last_heartbeat_at = stale_at
        job.attempt_count = 1
        await session.commit()

    status_response = await initialized_client.get(f"/api/v1/plot-analysis-jobs/{job_id}/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "pending"
    assert status_response.json()["stage"] is None

    async with app_with_db.state.session_factory() as session:
        job = await session.scalar(select(PlotAnalysisJob).where(PlotAnalysisJob.id == job_id))
        assert job is not None
        assert job.status == "pending"
        assert job.locked_by is None
        assert job.last_heartbeat_at is None


@pytest.mark.asyncio
async def test_worker_entrypoint_isolates_lane_failures_and_restarts_only_failed_lane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.worker as worker_module

    events: list[str] = []

    class FakeEngine:
        def __init__(self) -> None:
            self.dispose_calls = 0

        async def dispose(self) -> None:
            self.dispose_calls += 1

    class FakeStyleService:
        def __init__(self, label: str) -> None:
            self.label = label
            self.aclose_calls = 0

        async def run_worker(
            self,
            session_factory,
            *,
            poll_interval_seconds: float,
            max_poll_interval_seconds: float | None = None,
        ) -> None:
            del session_factory, poll_interval_seconds, max_poll_interval_seconds
            events.append(f"style-run:{self.label}")
            raise RuntimeError("style lane boom")

        async def aclose(self) -> None:
            self.aclose_calls += 1
            events.append(f"style-close:{self.label}")

    class FakePlotService:
        def __init__(self) -> None:
            self.aclose_calls = 0

        async def run_worker(
            self,
            session_factory,
            *,
            poll_interval_seconds: float,
            max_poll_interval_seconds: float | None = None,
        ) -> None:
            del session_factory, poll_interval_seconds, max_poll_interval_seconds
            events.append("plot-run")
            raise asyncio.CancelledError()

        async def aclose(self) -> None:
            self.aclose_calls += 1
            events.append("plot-close")

    fake_engine = FakeEngine()
    fake_session_factory = object()
    style_instances: list[FakeStyleService] = []
    plot_instances: list[FakePlotService] = []
    sleep_calls: list[float] = []

    def build_style_service() -> FakeStyleService:
        service = FakeStyleService(str(len(style_instances) + 1))
        style_instances.append(service)
        return service

    def build_plot_service() -> FakePlotService:
        service = FakePlotService()
        plot_instances.append(service)
        return service

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)
        if len(sleep_calls) >= 1:
            raise asyncio.CancelledError()

    settings = SimpleNamespace(
        style_analysis_worker_enabled=True,
        database_url="sqlite+aiosqlite:///./test.db",
        style_analysis_poll_interval_seconds=1.5,
        style_analysis_stale_timeout_seconds=30,
    )

    monkeypatch.setattr(worker_module, "get_settings", lambda: settings)
    monkeypatch.setattr(worker_module, "create_engine", lambda database_url: fake_engine)
    monkeypatch.setattr(worker_module, "create_session_factory", lambda engine: fake_session_factory)
    monkeypatch.setattr(worker_module, "StyleAnalysisWorkerService", build_style_service)
    monkeypatch.setattr(worker_module, "PlotAnalysisWorkerService", build_plot_service)
    monkeypatch.setattr(worker_module.asyncio, "sleep", fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        await worker_module.run_worker()

    assert events[:3] == ["style-run:1", "style-close:1", "plot-run"]
    assert "plot-close" in events
    assert len(style_instances) >= 1
    assert sleep_calls == [1.0]
    assert fake_engine.dispose_calls == 1
