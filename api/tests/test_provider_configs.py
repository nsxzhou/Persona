from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from httpx import AsyncClient


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
    assert refreshed["last_test_status"] is None
    assert refreshed["last_test_error"] is None


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
async def test_provider_config_repository_returns_first_user_id(
    app_with_db: FastAPI,
) -> None:
    from app.core.security import hash_password
    from app.db.repositories.auth import AuthRepository
    from app.db.repositories.provider_configs import ProviderConfigRepository

    async with app_with_db.state.session_factory() as session:
        user = await AuthRepository().create_user(
            session,
            username="provider-owner",
            password_hash=hash_password("password123"),
        )
        resolved_user_id = await ProviderConfigRepository().get_first_user_id(session)

    assert resolved_user_id == user.id


@pytest.mark.asyncio
async def test_provider_config_service_create_uses_repository_user_lookup() -> None:
    from app.schemas.provider_configs import ProviderConfigCreate
    from app.services.provider_configs import ProviderConfigService

    calls: list[str] = []

    class RepositoryStub:
        async def get_first_user_id(self, session) -> str | None:
            del session
            calls.append("get_first_user_id")
            return "user-1"

        async def create(
            self,
            session,
            *,
            label: str,
            base_url: str,
            api_key_encrypted: str,
            api_key_hint_last4: str,
            default_model: str,
            is_enabled: bool,
            user_id: str,
        ):
            del session
            calls.append("create")
            return SimpleNamespace(
                label=label,
                base_url=base_url,
                api_key_encrypted=api_key_encrypted,
                api_key_hint_last4=api_key_hint_last4,
                default_model=default_model,
                is_enabled=is_enabled,
                user_id=user_id,
            )

    service = ProviderConfigService(repository=RepositoryStub())  # type: ignore[arg-type]
    created_provider = await service.create(
        SimpleNamespace(),
        ProviderConfigCreate(
            label="Backup Gateway",
            base_url="https://gateway.example.com/v1",
            api_key="sk-backup-5678",
            default_model="gpt-4.1-nano",
            is_enabled=True,
        ),
    )

    assert calls == ["get_first_user_id", "create"]
    assert created_provider.user_id == "user-1"


@pytest.mark.asyncio
async def test_provider_config_service_create_without_users_raises_unprocessable_entity() -> None:
    from app.core.domain_errors import UnprocessableEntityError
    from app.schemas.provider_configs import ProviderConfigCreate
    from app.services.provider_configs import ProviderConfigService

    class RepositoryStub:
        async def get_first_user_id(self, session) -> str | None:
            del session
            return None

    service = ProviderConfigService(repository=RepositoryStub())  # type: ignore[arg-type]

    with pytest.raises(UnprocessableEntityError) as exc_info:
        await service.create(
            SimpleNamespace(),
            ProviderConfigCreate(
                label="Backup Gateway",
                base_url="https://gateway.example.com/v1",
                api_key="sk-backup-5678",
                default_model="gpt-4.1-nano",
                is_enabled=True,
            ),
        )

    assert exc_info.value.detail == "缺少用户上下文，无法创建 Provider"


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
