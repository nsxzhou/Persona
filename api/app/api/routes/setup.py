from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import set_session_cookie
from app.core.config import get_settings
from app.db.session import get_db_session
from app.schemas.provider_configs import ProviderConfigResponse
from app.schemas.setup import SetupRequest, SetupResponse, SetupStatusResponse
from app.services.auth import AuthService
from app.services.provider_configs import ProviderConfigService

router = APIRouter(prefix="/setup", tags=["setup"])

@router.get("/status", response_model=SetupStatusResponse)
async def get_setup_status(db_session: AsyncSession = Depends(get_db_session)) -> SetupStatusResponse:
    initialized = await AuthService().is_initialized(db_session)
    return SetupStatusResponse(initialized=initialized)

@router.post("", response_model=SetupResponse, status_code=status.HTTP_201_CREATED)
async def run_setup(payload: SetupRequest, response: Response, db_session: AsyncSession = Depends(get_db_session)) -> SetupResponse:
    auth_service = AuthService()
    provider_service = ProviderConfigService()
    if await auth_service.is_initialized(db_session):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="系统已初始化")

    user = await auth_service.create_initial_admin(db_session, payload.username, payload.password)
    provider = await provider_service.create(db_session, payload.provider)
    _, raw_token = await auth_service.create_session(db_session, user)

    set_session_cookie(response, raw_token)

    return SetupResponse(
        user=user,
        provider=ProviderConfigResponse(
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
        ),
    )

