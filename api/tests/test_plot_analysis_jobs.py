from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

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
