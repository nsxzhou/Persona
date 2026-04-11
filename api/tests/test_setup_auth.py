from __future__ import annotations

from typing import get_type_hints

import pytest
from httpx import AsyncClient


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
