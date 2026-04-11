from __future__ import annotations

from typing import get_type_hints

import pytest
from fastapi import FastAPI
from httpx import AsyncClient


def test_project_service_supports_repository_injection() -> None:
    from app.db.repositories.projects import ProjectRepository
    from app.services.projects import ProjectService

    repository = ProjectRepository()
    service = ProjectService(repository=repository)

    assert service.repository is repository


def test_projects_routes_use_annotated_service_dependency() -> None:
    from app.api.deps import DbSessionDep, ProjectServiceDep
    from app.api.routes.projects import list_projects

    hints = get_type_hints(list_projects, include_extras=True)

    assert hints["db_session"] == DbSessionDep
    assert hints["project_service"] == ProjectServiceDep


@pytest.mark.asyncio
async def test_project_service_can_bind_style_profile_id_by_project_id(
    app_with_db: FastAPI,
) -> None:
    from fastapi import HTTPException

    from app.schemas.projects import ProjectCreate
    from app.schemas.provider_configs import ProviderConfigCreate
    from app.services.projects import ProjectService
    from app.services.provider_configs import ProviderConfigService

    async with app_with_db.state.session_factory() as session:
        provider = await ProviderConfigService().create(
            session,
            ProviderConfigCreate(
                label="Primary Gateway",
                base_url="https://api.openai.com/v1",
                api_key="sk-test-8888",
                default_model="gpt-4.1-mini",
                is_enabled=True,
            ),
        )
        project = await ProjectService().create(
            session,
            ProjectCreate(
                name="Style Bind Target",
                description="用于测试 style_profile 绑定",
                status="draft",
                default_provider_id=provider.id,
                default_model="gpt-4.1-mini",
                style_profile_id=None,
            ),
        )

        target_style_profile_id = "11111111-1111-1111-1111-111111111111"
        updated = await ProjectService().set_style_profile_id(
            session,
            project.id,
            target_style_profile_id,
        )
        assert updated.id == project.id
        assert updated.style_profile_id == target_style_profile_id

        with pytest.raises(HTTPException) as exc_info:
            await ProjectService().set_style_profile_id(
                session,
                "non-existent-project-id",
                target_style_profile_id,
            )
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "项目不存在"


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
