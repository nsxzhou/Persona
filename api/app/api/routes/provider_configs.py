from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.deps import (
    CurrentUserDep,
    DbSessionDep,
    ProviderConfigServiceDep,
)
from app.schemas.provider_configs import (
    ConnectionTestResponse,
    ProviderConfigCreate,
    ProviderConfigResponse,
    ProviderConfigUpdate,
)
from app.services.llm_provider import LLMProviderService

router = APIRouter(
    prefix="/provider-configs",
    tags=["provider-configs"],
)

def _serialize(provider) -> ProviderConfigResponse:
    return ProviderConfigResponse(
        id=provider.id,
        label=provider.label,
        base_url=provider.base_url,
        default_model=provider.default_model,
        api_key_hint=f"****{provider.api_key_hint_last4}",
        is_enabled=provider.is_enabled,
        last_test_status=provider.last_test_status,
        last_test_error=provider.last_test_error,
        last_tested_at=provider.last_tested_at,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )

@router.get("", response_model=list[ProviderConfigResponse])
async def list_provider_configs(
    _current_user: CurrentUserDep,
    db_session: DbSessionDep,
    provider_service: ProviderConfigServiceDep,
) -> list[ProviderConfigResponse]:
    providers = await provider_service.list(db_session)
    return [_serialize(provider) for provider in providers]

@router.post("", response_model=ProviderConfigResponse, status_code=201)
async def create_provider_config(
    payload: ProviderConfigCreate,
    _current_user: CurrentUserDep,
    db_session: DbSessionDep,
    provider_service: ProviderConfigServiceDep,
) -> ProviderConfigResponse:
    provider = await provider_service.create(db_session, payload)
    return _serialize(provider)

@router.patch("/{provider_id}", response_model=ProviderConfigResponse)
async def update_provider_config(
    provider_id: str,
    payload: ProviderConfigUpdate,
    _current_user: CurrentUserDep,
    db_session: DbSessionDep,
    provider_service: ProviderConfigServiceDep,
) -> ProviderConfigResponse:
    provider = await provider_service.update(db_session, provider_id, payload)
    return _serialize(provider)

@router.post("/{provider_id}/test", response_model=ConnectionTestResponse)
async def test_provider_config(
    provider_id: str,
    _current_user: CurrentUserDep,
    db_session: DbSessionDep,
    provider_service: ProviderConfigServiceDep,
) -> ConnectionTestResponse:
    provider = await provider_service.get_or_404(db_session, provider_id)
    result = await LLMProviderService().test_connection(provider)
    await provider_service.update_test_result(
        db_session,
        provider,
        status_value=result["status"],
        error_message=None if result["status"] == "success" else result["message"],
    )

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return ConnectionTestResponse(**result)

@router.delete("/{provider_id}", status_code=204)
async def delete_provider_config(
    provider_id: str,
    _current_user: CurrentUserDep,
    db_session: DbSessionDep,
    provider_service: ProviderConfigServiceDep,
) -> None:
    await provider_service.delete(db_session, provider_id)
