from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.services.plot_analysis_worker import PlotAnalysisWorkerService


@pytest.mark.asyncio
async def test_plot_worker_caps_chunk_concurrency_to_one(
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
    assert observed["max_concurrency"] == 1

    get_settings.cache_clear()
