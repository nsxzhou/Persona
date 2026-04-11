from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import get_type_hints

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select


def test_auth_service_supports_repository_injection() -> None:
    from app.db.repositories.auth import AuthRepository
    from app.services.auth import AuthService

    repository = AuthRepository()
    service = AuthService(repository=repository)

    assert service.repository is repository


def test_auth_and_setup_routes_use_annotated_dependency_aliases() -> None:
    from app.api.deps import AuthServiceDep, DbSessionDep
    from app.api.routes.auth import login
    from app.api.routes.setup import run_setup

    login_hints = get_type_hints(login, include_extras=True)
    setup_hints = get_type_hints(run_setup, include_extras=True)

    assert login_hints["db_session"] == DbSessionDep
    assert login_hints["auth_service"] == AuthServiceDep
    assert setup_hints["db_session"] == DbSessionDep
    assert setup_hints["auth_service"] == AuthServiceDep


@pytest.mark.asyncio
async def test_setup_status_reports_uninitialized_for_empty_database(client: AsyncClient) -> None:
    response = await client.get("/api/v1/setup/status")

    assert response.status_code == 200
    assert response.json() == {"initialized": False}


@pytest.mark.asyncio
async def test_setup_creates_admin_provider_and_session_cookie(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/setup",
        json={
            "username": "persona-admin",
            "password": "super-secret-password",
            "provider": {
                "label": "Primary Gateway",
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-live-9876",
                "default_model": "gpt-4.1-mini",
                "is_enabled": True,
            },
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["user"]["username"] == "persona-admin"
    assert data["provider"]["label"] == "Primary Gateway"
    assert data["provider"]["api_key_hint"] == "****9876"
    assert "api_key" not in data["provider"]
    assert "persona_session" in response.cookies

    me_response = await client.get("/api/v1/me")
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "persona-admin"


@pytest.mark.asyncio
async def test_setup_rejects_second_initialization(initialized_client: AsyncClient) -> None:
    response = await initialized_client.post(
        "/api/v1/setup",
        json={
            "username": "another-admin",
            "password": "another-secret-password",
            "provider": {
                "label": "Backup Gateway",
                "base_url": "https://api.deepseek.com",
                "api_key": "sk-another-1111",
                "default_model": "deepseek-chat",
                "is_enabled": True,
            },
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "系统已初始化"


@pytest.mark.asyncio
async def test_login_logout_and_me_flow(initialized_client: AsyncClient) -> None:
    await initialized_client.post("/api/v1/logout")

    unauthorized = await initialized_client.get("/api/v1/me")
    assert unauthorized.status_code == 401

    bad_login = await initialized_client.post(
        "/api/v1/login",
        json={"username": "persona-admin", "password": "wrong-password"},
    )
    assert bad_login.status_code == 401

    good_login = await initialized_client.post(
        "/api/v1/login",
        json={"username": "persona-admin", "password": "super-secret-password"},
    )
    assert good_login.status_code == 200
    assert "persona_session" in good_login.cookies

    me_response = await initialized_client.get("/api/v1/me")
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "persona-admin"

    logout_response = await initialized_client.post("/api/v1/logout")
    assert logout_response.status_code == 204

    after_logout = await initialized_client.get("/api/v1/me")
    assert after_logout.status_code == 401


@pytest.mark.asyncio
async def test_authenticate_raises_domain_error_for_invalid_credentials() -> None:
    from app.core.domain_errors import UnauthorizedError
    from app.services.auth import AuthService

    class RepoStub:
        async def get_user_by_username(self, session, username: str):
            del session, username
            return None

    service = AuthService(repository=RepoStub())  # type: ignore[arg-type]

    with pytest.raises(UnauthorizedError) as exc_info:
        await service.authenticate(
            session=SimpleNamespace(),
            username="persona-admin",
            password="wrong-password",
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "账号或密码错误"


@pytest.mark.asyncio
async def test_resolve_user_by_token_uses_session_user_and_throttles_last_access_write() -> None:
    from app.services.auth import AuthService

    now = datetime.now(UTC)
    user = SimpleNamespace(id="user-1", username="persona-admin")
    session_record = SimpleNamespace(
        id="session-1",
        user_id="user-1",
        user=user,
        expires_at=now + timedelta(hours=1),
        last_accessed_at=now - timedelta(seconds=30),
    )

    class RepoStub:
        flush_calls = 0

        async def get_session_by_token_hash(self, session, token_hash: str):
            del session, token_hash
            return session_record

        async def flush(self, session) -> None:
            del session
            self.flush_calls += 1

        async def get_user_by_id(self, session, user_id: str):
            del session, user_id
            raise AssertionError("resolve_user_by_token should not do a second user lookup")

    repository = RepoStub()
    service = AuthService(repository=repository)  # type: ignore[arg-type]

    resolved_user = await service.resolve_user_by_token(session=None, raw_token="test-token")

    assert resolved_user is user
    assert repository.flush_calls == 0


@pytest.mark.asyncio
async def test_resolve_user_by_token_updates_last_access_after_throttle_window() -> None:
    from app.services.auth import AuthService

    now = datetime.now(UTC)
    user = SimpleNamespace(id="user-1", username="persona-admin")
    session_record = SimpleNamespace(
        id="session-1",
        user_id="user-1",
        user=user,
        expires_at=now + timedelta(hours=1),
        last_accessed_at=now - timedelta(hours=1),
    )

    class RepoStub:
        flush_calls = 0

        async def get_session_by_token_hash(self, session, token_hash: str):
            del session, token_hash
            return session_record

        async def flush(self, session) -> None:
            del session
            self.flush_calls += 1

        async def get_user_by_id(self, session, user_id: str):
            del session, user_id
            raise AssertionError("resolve_user_by_token should not do a second user lookup")

    repository = RepoStub()
    service = AuthService(repository=repository)  # type: ignore[arg-type]

    before = session_record.last_accessed_at
    resolved_user = await service.resolve_user_by_token(session=None, raw_token="test-token")

    assert resolved_user is user
    assert repository.flush_calls == 1
    assert session_record.last_accessed_at > before


@pytest.mark.asyncio
async def test_delete_account_cleans_style_lab_rows_and_sample_files(
    initialized_client: AsyncClient,
    app_with_db,
) -> None:
    from app.core.config import get_settings
    from app.db.models import (
        Project,
        ProviderConfig,
        StyleAnalysisJob,
        StyleProfile,
        StyleSampleFile,
        User,
    )
    from app.services.style_analysis_storage import StyleAnalysisStorageService

    provider_id = (await initialized_client.get("/api/v1/provider-configs")).json()[0]["id"]
    create_job_response = await initialized_client.post(
        "/api/v1/style-analysis-jobs",
        data={"style_name": "删除账号清理验证", "provider_id": provider_id},
        files={"file": ("sample.txt", "夜雨。".encode("utf-8"), "text/plain")},
    )
    assert create_job_response.status_code == 201
    sample_file_id = create_job_response.json()["sample_file"]["id"]

    sample_file_path = Path(get_settings().storage_dir) / "style-samples" / f"{sample_file_id}.txt"
    assert sample_file_path.exists() is True
    storage_service = StyleAnalysisStorageService()
    await storage_service.write_chunk_artifact(create_job_response.json()["id"], 0, "中间产物")
    artifact_dir = Path(get_settings().storage_dir) / "style-analysis-artifacts" / create_job_response.json()["id"]
    assert artifact_dir.exists() is True

    delete_response = await initialized_client.delete("/api/v1/account")
    assert delete_response.status_code == 204
    assert sample_file_path.exists() is False
    assert artifact_dir.exists() is False

    setup_status_response = await initialized_client.get("/api/v1/setup/status")
    assert setup_status_response.status_code == 200
    assert setup_status_response.json() == {"initialized": False}

    async with app_with_db.state.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(User)) == 0
        assert await session.scalar(select(func.count()).select_from(ProviderConfig)) == 0
        assert await session.scalar(select(func.count()).select_from(Project)) == 0
        assert await session.scalar(select(func.count()).select_from(StyleAnalysisJob)) == 0
        assert await session.scalar(select(func.count()).select_from(StyleProfile)) == 0
        assert await session.scalar(select(func.count()).select_from(StyleSampleFile)) == 0


@pytest.mark.asyncio
async def test_list_style_lab_cleanup_targets_uses_stream_scalars() -> None:
    from app.db.repositories.auth import AuthRepository

    class StreamResult:
        def __init__(self, values):
            self._values = values

        def all(self):  # pragma: no cover - this should not be used
            raise AssertionError("list_style_lab_cleanup_targets should not call .all()")

        def __aiter__(self):
            async def iterator():
                for value in self._values:
                    yield value

            return iterator()

    class SessionStub:
        def __init__(self) -> None:
            self.calls = 0

        async def stream_scalars(self, stmt):
            del stmt
            self.calls += 1
            if self.calls == 1:
                return StreamResult(["/tmp/a.txt", "", None, "/tmp/b.txt"])
            return StreamResult(["job-1", None, "job-2"])

    repository = AuthRepository()
    sample_paths, job_ids = await repository.list_style_lab_cleanup_targets(SessionStub())

    assert sample_paths == ["/tmp/a.txt", "/tmp/b.txt"]
    assert job_ids == ["job-1", "job-2"]
