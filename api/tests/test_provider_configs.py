from __future__ import annotations

from typing import get_type_hints

import pytest
from httpx import AsyncClient


def test_provider_service_supports_repository_injection() -> None:
    from app.db.repositories.provider_configs import ProviderConfigRepository
    from app.services.provider_configs import ProviderConfigService

    repository = ProviderConfigRepository()
    service = ProviderConfigService(repository=repository)

    assert service.repository is repository


def test_provider_routes_use_annotated_service_dependency() -> None:
    from app.api.deps import DbSessionDep, ProviderConfigServiceDep
    from app.api.routes.provider_configs import list_provider_configs

    hints = get_type_hints(list_provider_configs, include_extras=True)

    assert hints["db_session"] == DbSessionDep
    assert hints["provider_service"] == ProviderConfigServiceDep


@pytest.mark.asyncio
async def test_provider_configs_mask_keys_and_support_crud(initialized_client: AsyncClient) -> None:
    list_response = await initialized_client.get("/api/v1/provider-configs")
    assert list_response.status_code == 200
    providers = list_response.json()
    assert len(providers) == 1
    assert providers[0]["api_key_hint"] == "****1234"
    assert "api_key_encrypted" not in providers[0]

    create_response = await initialized_client.post(
        "/api/v1/provider-configs",
        json={
            "label": "Backup Gateway",
            "base_url": "https://gateway.example.com/v1",
            "api_key": "sk-backup-5678",
            "default_model": "gpt-4.1-nano",
            "is_enabled": True,
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["label"] == "Backup Gateway"
    assert created["api_key_hint"] == "****5678"

    update_response = await initialized_client.patch(
        f"/api/v1/provider-configs/{created['id']}",
        json={
            "label": "Backup Gateway Updated",
            "default_model": "gpt-4.1-mini",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["label"] == "Backup Gateway Updated"
    assert update_response.json()["default_model"] == "gpt-4.1-mini"


@pytest.mark.asyncio
async def test_provider_connection_test_updates_status(initialized_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.llm_provider import LLMProviderService

    async def fake_test_connection(self, provider_config):  # type: ignore[no-untyped-def]
        return {"status": "success", "message": "连接成功"}

    monkeypatch.setattr(LLMProviderService, "test_connection", fake_test_connection)

    providers = (await initialized_client.get("/api/v1/provider-configs")).json()
    provider_id = providers[0]["id"]

    response = await initialized_client.post(f"/api/v1/provider-configs/{provider_id}/test")

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["message"] == "连接成功"

    refreshed = (await initialized_client.get("/api/v1/provider-configs")).json()[0]
    assert refreshed["last_test_status"] == "success"


@pytest.mark.asyncio
async def test_provider_delete_rejects_when_referenced_by_active_project(initialized_client: AsyncClient) -> None:
    providers = (await initialized_client.get("/api/v1/provider-configs")).json()
    provider_id = providers[0]["id"]

    project_response = await initialized_client.post(
        "/api/v1/projects",
        json={
            "name": "Glass City",
            "description": "都市悬疑长篇",
            "status": "active",
            "default_provider_id": provider_id,
            "default_model": "gpt-4.1-mini",
            "style_profile_id": None,
        },
    )
    assert project_response.status_code == 201

    delete_response = await initialized_client.delete(f"/api/v1/provider-configs/{provider_id}")

    assert delete_response.status_code == 409
    assert delete_response.json()["detail"] == "该 Provider 正被项目引用，无法删除"


@pytest.mark.asyncio
async def test_provider_update_accepts_empty_api_key_as_keep_original(initialized_client: AsyncClient) -> None:
    providers = (await initialized_client.get("/api/v1/provider-configs")).json()
    provider_id = providers[0]["id"]
    original_hint = providers[0]["api_key_hint"]

    update_response = await initialized_client.patch(
        f"/api/v1/provider-configs/{provider_id}",
        json={
            "label": "Primary Gateway",
            "api_key": "",
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["api_key_hint"] == original_hint
