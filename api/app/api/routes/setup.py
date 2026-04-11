from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.api.deps import (
    AuthServiceDep,
    DbSessionDep,
    ProviderConfigServiceDep,
    set_session_cookie,
)
from app.core.domain_errors import DomainError, to_http_exception
from app.schemas.provider_configs import ProviderConfigResponse
from app.schemas.setup import SetupRequest, SetupResponse, SetupStatusResponse

router = APIRouter(prefix="/setup", tags=["setup"])

@router.get("/status", response_model=SetupStatusResponse)
async def get_setup_status(
    db_session: DbSessionDep,
    auth_service: AuthServiceDep,
) -> SetupStatusResponse:
    initialized = await auth_service.is_initialized(db_session)
    return SetupStatusResponse(initialized=initialized)

@router.post("", response_model=SetupResponse, status_code=status.HTTP_201_CREATED)
async def run_setup(
    payload: SetupRequest,
    response: Response,
    db_session: DbSessionDep,
    auth_service: AuthServiceDep,
    provider_service: ProviderConfigServiceDep,
) -> SetupResponse:
    try:
        await auth_service.ensure_not_initialized(db_session)
        user = await auth_service.create_initial_admin(db_session, payload.username, payload.password)
        provider = await provider_service.create(db_session, payload.provider)
        _, raw_token = await auth_service.create_session(db_session, user)
    except DomainError as exc:
        raise to_http_exception(exc) from exc

    set_session_cookie(response, raw_token)

    return SetupResponse(
        user=user,
        provider=ProviderConfigResponse.model_validate(provider),
    )
