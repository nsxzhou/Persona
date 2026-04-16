from __future__ import annotations

from fastapi import APIRouter

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

router = APIRouter(
    prefix="/provider-configs",
    tags=["provider-configs"],
)

@router.get("", response_model=list[ProviderConfigResponse])
async def list_provider_configs(
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    provider_service: ProviderConfigServiceDep,
) -> list[ProviderConfigResponse]:
    providers = await provider_service.list(db_session, user_id=current_user.id)
    return [ProviderConfigResponse.model_validate(provider) for provider in providers]

@router.post("", response_model=ProviderConfigResponse, status_code=201)
async def create_provider_config(
    payload: ProviderConfigCreate,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    provider_service: ProviderConfigServiceDep,
) -> ProviderConfigResponse:
    provider = await provider_service.create(
        db_session,
        payload,
        user_id=current_user.id,
    )
    return ProviderConfigResponse.model_validate(provider)

@router.patch("/{provider_id}", response_model=ProviderConfigResponse)
async def update_provider_config(
    provider_id: str,
    payload: ProviderConfigUpdate,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    provider_service: ProviderConfigServiceDep,
) -> ProviderConfigResponse:
    provider = await provider_service.update(
        db_session,
        provider_id,
        payload,
        user_id=current_user.id,
    )
    return ProviderConfigResponse.model_validate(provider)

@router.post("/{provider_id}/test", response_model=ConnectionTestResponse)
async def test_provider_config(
    provider_id: str,
    _current_user: CurrentUserDep,
    db_session: DbSessionDep,
    provider_service: ProviderConfigServiceDep,
) -> ConnectionTestResponse:
    result = await provider_service.test_connection_and_update(
        db_session,
        provider_id,
        user_id=getattr(_current_user, "id", None),
    )
    return ConnectionTestResponse(**result)

@router.delete("/{provider_id}", status_code=204)
async def delete_provider_config(
    provider_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    provider_service: ProviderConfigServiceDep,
) -> None:
    await provider_service.delete(
        db_session,
        provider_id,
        user_id=current_user.id,
    )
