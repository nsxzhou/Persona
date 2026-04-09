from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


@pytest.fixture
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


@pytest.fixture
async def client(app_with_db: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app_with_db),
        base_url="http://testserver",
    ) as async_client:
        yield async_client



@pytest.fixture
async def initialized_client(client: AsyncClient) -> AsyncClient:
    response = await client.post(
        "/api/v1/setup",
        json={
            "username": "persona-admin",
            "password": "super-secret-password",
            "provider": {
                "label": "Primary Gateway",
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-test-1234",
                "default_model": "gpt-4.1-mini",
                "is_enabled": True,
            },
        },
    )
    assert response.status_code == 201
    return client
