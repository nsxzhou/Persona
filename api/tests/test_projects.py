from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_project_crud_archive_restore_and_filtering(initialized_client: AsyncClient) -> None:
    provider_id = (await initialized_client.get("/api/v1/provider-configs")).json()[0]["id"]

    create_response = await initialized_client.post(
        "/api/v1/projects",
        json={
            "name": "Immortal River Chronicle",
            "description": "东方玄幻长篇项目",
            "status": "draft",
            "default_provider_id": provider_id,
            "default_model": "",
            "style_profile_id": None,
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["default_model"] == "gpt-4.1-mini"
    assert created["provider"]["id"] == provider_id

    list_response = await initialized_client.get("/api/v1/projects")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    update_response = await initialized_client.patch(
        f"/api/v1/projects/{created['id']}",
        json={
            "description": "东方玄幻长篇项目（已调整）",
            "status": "active",
            "default_model": "gpt-4.1",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "active"
    assert update_response.json()["default_model"] == "gpt-4.1"

    archive_response = await initialized_client.post(f"/api/v1/projects/{created['id']}/archive")
    assert archive_response.status_code == 200
    assert archive_response.json()["archived_at"] is not None

    default_list = await initialized_client.get("/api/v1/projects")
    assert default_list.status_code == 200
    assert default_list.json() == []

    include_archived = await initialized_client.get("/api/v1/projects?include_archived=true")
    assert include_archived.status_code == 200
    assert len(include_archived.json()) == 1

    restore_response = await initialized_client.post(f"/api/v1/projects/{created['id']}/restore")
    assert restore_response.status_code == 200
    assert restore_response.json()["archived_at"] is None


@pytest.mark.asyncio
async def test_project_creation_rejects_disabled_provider(initialized_client: AsyncClient) -> None:
    provider = (
        await initialized_client.post(
            "/api/v1/provider-configs",
            json={
                "label": "Disabled Gateway",
                "base_url": "https://gateway.example.com/v1",
                "api_key": "sk-disabled-0000",
                "default_model": "gpt-4.1-mini",
                "is_enabled": False,
            },
        )
    ).json()

    response = await initialized_client.post(
        "/api/v1/projects",
        json={
            "name": "Should Fail",
            "description": "禁用 provider 不应可用",
            "status": "draft",
            "default_provider_id": provider["id"],
            "default_model": "gpt-4.1-mini",
            "style_profile_id": None,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "默认 Provider 不存在或未启用"

