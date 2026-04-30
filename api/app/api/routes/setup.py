from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.api.deps import (
    AuthServiceDep,
    DbSessionDep,
    SetupServiceDep,
    set_session_cookie,
)
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
    setup_service: SetupServiceDep,
) -> SetupResponse:
    result = await setup_service.run_initial_setup(db_session, payload)
    set_session_cookie(response, result.raw_token)

    return SetupResponse(
        user=result.user,
        provider=ProviderConfigResponse.model_validate(result.provider),
    )
