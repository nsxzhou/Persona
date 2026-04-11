from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import CurrentUserDep, DbSessionDep, StyleProfileServiceDep
from app.schemas.style_profiles import (
    StyleProfileCreate,
    StyleProfileListItemResponse,
    StyleProfileResponse,
    StyleProfileUpdate,
)
from app.services.style_analysis_jobs import build_profile_result_bundle

router = APIRouter(
    prefix="/style-profiles",
    tags=["style-profiles"],
)

def _serialize(profile) -> StyleProfileResponse:
    analysis_report, style_summary, prompt_pack = build_profile_result_bundle(profile)
    return StyleProfileResponse(
        id=profile.id,
        source_job_id=profile.source_job_id,
        provider_id=profile.provider_id,
        model_name=profile.model_name,
        source_filename=profile.source_filename,
        style_name=profile.style_name,
        analysis_report=analysis_report,
        style_summary=style_summary,
        prompt_pack=prompt_pack,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _serialize_list_item(profile) -> StyleProfileListItemResponse:
    return StyleProfileListItemResponse(
        id=profile.id,
        provider_id=profile.provider_id,
        model_name=profile.model_name,
        source_filename=profile.source_filename,
        style_name=profile.style_name,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.get("", response_model=list[StyleProfileListItemResponse])
async def list_style_profiles(
    _current_user: CurrentUserDep,
    db_session: DbSessionDep,
    style_profile_service: StyleProfileServiceDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
) -> list[StyleProfileListItemResponse]:
    profiles = await style_profile_service.list(db_session, offset=offset, limit=limit)
    return [_serialize_list_item(profile) for profile in profiles]

@router.get("/{profile_id}", response_model=StyleProfileResponse)
async def get_style_profile(
    profile_id: str,
    _current_user: CurrentUserDep,
    db_session: DbSessionDep,
    style_profile_service: StyleProfileServiceDep,
) -> StyleProfileResponse:
    profile = await style_profile_service.get_or_404(db_session, profile_id)
    return _serialize(profile)

@router.post("", response_model=StyleProfileResponse, status_code=201)
async def create_style_profile(
    payload: StyleProfileCreate,
    _current_user: CurrentUserDep,
    db_session: DbSessionDep,
    style_profile_service: StyleProfileServiceDep,
) -> StyleProfileResponse:
    profile = await style_profile_service.create(db_session, payload)
    return _serialize(profile)

@router.patch("/{profile_id}", response_model=StyleProfileResponse)
async def update_style_profile(
    profile_id: str,
    payload: StyleProfileUpdate,
    _current_user: CurrentUserDep,
    db_session: DbSessionDep,
    style_profile_service: StyleProfileServiceDep,
) -> StyleProfileResponse:
    profile = await style_profile_service.update(db_session, profile_id, payload)
    return _serialize(profile)
