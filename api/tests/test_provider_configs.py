from __future__ import annotations

from types import SimpleNamespace
from typing import get_type_hints

import pytest
from fastapi import HTTPException
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
async def test_provider_configs_mask_keys_and_support_crud(
    initialized_client: AsyncClient,
    default_provider_api_key_hint: str,
) -> None:
    list_response = await initialized_client.get("/api/v1/provider-configs")
    assert list_response.status_code == 200
    providers = list_response.json()
    assert len(providers) == 1
    assert providers[0]["api_key_hint"] == default_provider_api_key_hint
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
async def test_provider_connection_test_masks_sensitive_error_details(
    initialized_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.llm_provider import LLMProviderService

    async def fake_test_connection(self, provider_config):  # type: ignore[no-untyped-def]
        del provider_config
        return {"status": "error", "message": "upstream timeout: sk-secret-1234"}

    monkeypatch.setattr(LLMProviderService, "test_connection", fake_test_connection)

    provider_id = (await initialized_client.get("/api/v1/provider-configs")).json()[0]["id"]
    response = await initialized_client.post(f"/api/v1/provider-configs/{provider_id}/test")

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail.startswith("Provider 连通性测试失败，请检查配置后重试（原因：")
    assert "sk-secret-1234" not in detail
    assert "[REDACTED]" in detail

    refreshed = (await initialized_client.get("/api/v1/provider-configs")).json()[0]
    assert refreshed["last_test_status"] == "error"
    assert refreshed["last_test_error"] == "upstream timeout: [REDACTED]"


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
async def test_provider_delete_rejects_when_referenced_by_style_analysis_job(
    initialized_client: AsyncClient,
) -> None:
    provider_id = (await initialized_client.get("/api/v1/provider-configs")).json()[0]["id"]

    create_job_response = await initialized_client.post(
        "/api/v1/style-analysis-jobs",
        data={"style_name": "Provider 引用校验", "provider_id": provider_id},
        files={"file": ("sample.txt", "风很冷。".encode("utf-8"), "text/plain")},
    )
    assert create_job_response.status_code == 201

    delete_response = await initialized_client.delete(f"/api/v1/provider-configs/{provider_id}")

    assert delete_response.status_code == 409
    assert delete_response.json()["detail"] == "该 Provider 正被 Style Lab 引用，无法删除"


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


@pytest.mark.asyncio
async def test_provider_delete_uses_repository_style_lab_reference_check() -> None:
    from app.core.domain_errors import ConflictError
    from app.services.provider_configs import ProviderConfigService

    provider = SimpleNamespace(id="provider-1", projects=[])

    class RepositoryStub:
        async def get_with_projects(self, session, provider_id: str, *, user_id: str | None = None):
            del session, provider_id, user_id
            return provider

        async def has_style_lab_references(self, session, provider_id: str, *, user_id: str | None = None) -> bool:
            del session, provider_id, user_id
            return True

        async def delete(self, session, provider):  # pragma: no cover - should not be reached
            del session, provider
            raise AssertionError("delete should not be called when references exist")

    service = ProviderConfigService(repository=RepositoryStub())  # type: ignore[arg-type]
    with pytest.raises(ConflictError) as exc_info:
        await service.delete(session=SimpleNamespace(), provider_id="provider-1")

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "该 Provider 正被 Style Lab 引用，无法删除"
    assert not isinstance(exc_info.value, HTTPException)


@pytest.mark.asyncio
async def test_provider_test_route_maps_domain_error_without_manual_commit() -> None:
    from app.api.routes.provider_configs import test_provider_config
    from app.core.domain_errors import BadRequestError

    class FakeSession:
        def __init__(self) -> None:
            self.commit_calls = 0

        async def commit(self) -> None:
            self.commit_calls += 1

    class FakeProviderService:
        async def test_connection_and_update(
            self,
            session,
            provider_id: str,
            *,
            user_id: str | None = None,
        ) -> dict[str, str]:
            del session, provider_id, user_id
            raise BadRequestError("Provider 连通性测试失败，请检查配置后重试")

    session = FakeSession()
    with pytest.raises(BadRequestError) as exc_info:
        await test_provider_config(
            provider_id="provider-1",
            _current_user=SimpleNamespace(),
            db_session=session,  # type: ignore[arg-type]
            provider_service=FakeProviderService(),  # type: ignore[arg-type]
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Provider 连通性测试失败，请检查配置后重试"
    assert session.commit_calls == 0
