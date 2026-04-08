from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.provider_configs import (
    ConnectionTestResponse,
    ProviderConfigCreate,
    ProviderConfigResponse,
    ProviderConfigUpdate,
)
from app.services.llm_provider import LLMProviderService
from app.services.provider_configs import ProviderConfigService

router = APIRouter(prefix="/provider-configs", tags=["provider-configs"])


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
    db_session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[ProviderConfigResponse]:
    del current_user
    providers = await ProviderConfigService().list(db_session)
    return [_serialize(provider) for provider in providers]


@router.post("", response_model=ProviderConfigResponse, status_code=201)
async def create_provider_config(
    payload: ProviderConfigCreate,
    db_session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ProviderConfigResponse:
    del current_user
    provider = await ProviderConfigService().create(db_session, payload)
    await db_session.commit()
    return _serialize(provider)


@router.patch("/{provider_id}", response_model=ProviderConfigResponse)
async def update_provider_config(
    provider_id: str,
    payload: ProviderConfigUpdate,
    db_session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ProviderConfigResponse:
    del current_user
    provider = await ProviderConfigService().update(db_session, provider_id, payload)
    await db_session.commit()
    return _serialize(provider)


@router.post("/{provider_id}/test", response_model=ConnectionTestResponse)
async def test_provider_config(
    provider_id: str,
    db_session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ConnectionTestResponse:
    del current_user
    provider_service = ProviderConfigService()
    provider = await provider_service.get_or_404(db_session, provider_id)
    result = await LLMProviderService().test_connection(provider)
    await provider_service.update_test_result(
        db_session,
        provider,
        status_value=result["status"],
        error_message=None if result["status"] == "success" else result["message"],
    )
    await db_session.commit()
    return ConnectionTestResponse(**result)


@router.delete("/{provider_id}", status_code=204)
async def delete_provider_config(
    provider_id: str,
    db_session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    del current_user
    await ProviderConfigService().delete(db_session, provider_id)
    await db_session.commit()

