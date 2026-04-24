from __future__ import annotations

import os
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DEFAULT_PROVIDER_PAYLOAD = {
    "label": "Test Provider",
    "base_url": "https://api.example.test/v1",
    "api_key": "sk-test-1234",
    "default_model": "gpt-4.1-mini",
    "is_enabled": True,
}


def _require_live_provider_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    pytest.fail(f"缺少真实 Provider 测试环境变量：{name}")


@pytest.fixture
def live_provider_payload() -> dict[str, Any]:
    return {
        "label": os.environ.get("PERSONA_TEST_PROVIDER_LABEL", "Live Test Provider").strip()
        or "Live Test Provider",
        "base_url": _require_live_provider_env("PERSONA_TEST_PROVIDER_BASE_URL"),
        "api_key": _require_live_provider_env("PERSONA_TEST_PROVIDER_API_KEY"),
        "default_model": _require_live_provider_env("PERSONA_TEST_PROVIDER_MODEL"),
        "is_enabled": True,
    }


@pytest.fixture
def live_provider_api_key_hint(live_provider_payload: dict[str, Any]) -> str:
    api_key = str(live_provider_payload["api_key"])
    return f"****{api_key[-4:]}"


@pytest.fixture
def default_provider_payload() -> dict[str, Any]:
    return dict(DEFAULT_PROVIDER_PAYLOAD)


@pytest.fixture
def default_provider_api_key_hint(default_provider_payload: dict[str, Any]) -> str:
    api_key = str(default_provider_payload["api_key"])
    return f"****{api_key[-4:]}"


@pytest.fixture
def live_style_analysis_sample_text() -> str:
    sample_path = Path(__file__).parent / "sample_novel.txt"
    if sample_path.exists():
        return sample_path.read_text(encoding="utf-8")
    # Fallback just in case the file is missing
    return "测试片段缺失，请确保 tests/sample_novel.txt 存在。"


@pytest_asyncio.fixture
async def app_with_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[FastAPI]:
    db_path = tmp_path / "persona-test.db"
    storage_dir = tmp_path / "storage"
    monkeypatch.setenv("PERSONA_DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    monkeypatch.setenv("PERSONA_SESSION_COOKIE_SECURE", "false")
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(storage_dir))
    monkeypatch.setenv("PERSONA_STYLE_ANALYSIS_WORKER_ENABLED", "false")

    from app.core.config import get_settings
    from app.db.base import Base
    from app.db.session import create_engine, create_session_factory
    from app.main import create_app

    get_settings.cache_clear()
    settings = get_settings()
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    app = create_app(session_factory=session_factory)
    yield app
    await engine.dispose()


@pytest_asyncio.fixture
async def client(app_with_db: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app_with_db),
        base_url="http://testserver",
    ) as async_client:
        yield async_client


async def _initialize_client(
    client: AsyncClient,
    *,
    provider_payload: dict[str, Any],
) -> AsyncClient:
    response = await client.post(
        "/api/v1/setup",
        json={
            "username": "persona-admin",
            "password": "super-secret-password",
            "provider": provider_payload,
        },
    )
    assert response.status_code == 201
    return client


@pytest_asyncio.fixture
async def initialized_client(
    client: AsyncClient,
    default_provider_payload: dict[str, Any],
) -> AsyncClient:
    return await _initialize_client(
        client,
        provider_payload=default_provider_payload,
    )


@pytest_asyncio.fixture
async def initialized_provider(initialized_client: AsyncClient) -> dict[str, Any]:
    response = await initialized_client.get("/api/v1/provider-configs")
    assert response.status_code == 200
    providers = response.json()
    assert len(providers) == 1
    return providers[0]


@pytest_asyncio.fixture
async def initialized_live_client(
    client: AsyncClient,
    live_provider_payload: dict[str, Any],
) -> AsyncClient:
    return await _initialize_client(
        client,
        provider_payload=live_provider_payload,
    )


@pytest_asyncio.fixture
async def initialized_live_provider(initialized_live_client: AsyncClient) -> dict[str, Any]:
    response = await initialized_live_client.get("/api/v1/provider-configs")
    assert response.status_code == 200
    providers = response.json()
    assert len(providers) == 1
    return providers[0]


@pytest.fixture
def run_live_style_analysis_job(
    initialized_live_client: AsyncClient,
    app_with_db: FastAPI,
    initialized_live_provider: dict[str, Any],
    live_style_analysis_sample_text: str,
) -> Callable[..., Awaitable[dict[str, Any]]]:
    from app.services.style_analysis_worker import StyleAnalysisWorkerService
    from app.core.config import get_settings

    async def _run(
        *,
        style_name: str,
        sample_text: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "style_name": style_name,
            "provider_id": initialized_live_provider["id"],
        }
        if model:
            payload["model"] = model
        create_response = await initialized_live_client.post(
            "/api/v1/style-analysis-jobs",
            data=payload,
            files={
                "file": (
                    "sample.txt",
                    (sample_text or live_style_analysis_sample_text).encode("utf-8"),
                    "text/plain",
                )
            },
        )
        assert create_response.status_code == 201
        job = create_response.json()
        service = StyleAnalysisWorkerService()
        settings = get_settings()
        attempts = max(1, int(settings.style_analysis_max_attempts))
        detail = None
        for _ in range(attempts):
            processed = await service.process_next_pending(app_with_db.state.session_factory)
            assert processed is True
            detail_response = await initialized_live_client.get(
                f"/api/v1/style-analysis-jobs/{job['id']}"
            )
            assert detail_response.status_code == 200
            detail = detail_response.json()
            if detail["status"] in ("succeeded", "failed"):
                break
        return {
            "job": job,
            "detail": detail,
        }

    return _run


@pytest.fixture
def run_live_plot_analysis_job(
    initialized_live_client: AsyncClient,
    app_with_db: FastAPI,
    initialized_live_provider: dict[str, Any],
    live_style_analysis_sample_text: str,
) -> Callable[..., Awaitable[dict[str, Any]]]:
    from app.services.plot_analysis_worker import PlotAnalysisWorkerService
    from app.core.config import get_settings

    async def _run(
        *,
        plot_name: str,
        sample_text: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "plot_name": plot_name,
            "provider_id": initialized_live_provider["id"],
        }
        if model:
            payload["model"] = model
        create_response = await initialized_live_client.post(
            "/api/v1/plot-analysis-jobs",
            data=payload,
            files={
                "file": (
                    "sample.txt",
                    (sample_text or live_style_analysis_sample_text).encode("utf-8"),
                    "text/plain",
                )
            },
        )
        assert create_response.status_code == 201
        job = create_response.json()
        service = PlotAnalysisWorkerService()
        settings = get_settings()
        attempts = max(1, int(settings.style_analysis_max_attempts))
        detail = None
        for _ in range(attempts):
            processed = await service.process_next_pending(app_with_db.state.session_factory)
            assert processed is True
            detail_response = await initialized_live_client.get(
                f"/api/v1/plot-analysis-jobs/{job['id']}"
            )
            assert detail_response.status_code == 200
            detail = detail_response.json()
            if detail["status"] in ("succeeded", "failed"):
                break
        if detail and detail["status"] != "succeeded":
            logs_response = await initialized_live_client.get(
                f"/api/v1/plot-analysis-jobs/{job['id']}/logs"
            )
            print("PLOT_JOB_DETAIL", detail)
            print("PLOT_JOB_LOGS", logs_response.text)
        return {
            "job": job,
            "detail": detail,
        }

    return _run
