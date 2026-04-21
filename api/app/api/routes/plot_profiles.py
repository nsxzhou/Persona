from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.api.assemblers import build_plot_profile_response_payload
from app.api.deps import CurrentUserDep, DbSessionDep, PlotProfileServiceDep
from app.schemas.plot_profiles import (
    PlotProfileCreate,
    PlotProfileListItemResponse,
    PlotProfileResponse,
    PlotProfileUpdate,
)

router = APIRouter(
    prefix="/plot-profiles",
    tags=["plot-profiles"],
)


def _serialize(profile) -> PlotProfileResponse:
    return PlotProfileResponse(**build_plot_profile_response_payload(profile))


def _serialize_list_item(profile) -> PlotProfileListItemResponse:
    return PlotProfileListItemResponse(
        id=profile.id,
        provider_id=profile.provider_id,
        model_name=profile.model_name,
        source_filename=profile.source_filename,
        plot_name=profile.plot_name,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.get("", response_model=list[PlotProfileListItemResponse])
async def list_plot_profiles(
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    plot_profile_service: PlotProfileServiceDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
) -> list[PlotProfileListItemResponse]:
    profiles = await plot_profile_service.list(
        db_session,
        user_id=current_user.id,
        offset=offset,
        limit=limit,
    )
    return [_serialize_list_item(profile) for profile in profiles]


@router.get("/{profile_id}", response_model=PlotProfileResponse)
async def get_plot_profile(
    profile_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    plot_profile_service: PlotProfileServiceDep,
) -> PlotProfileResponse:
    profile = await plot_profile_service.get_or_404(
        db_session,
        profile_id,
        user_id=current_user.id,
    )
    return _serialize(profile)


@router.post("", response_model=PlotProfileResponse, status_code=201)
async def create_plot_profile(
    payload: PlotProfileCreate,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    plot_profile_service: PlotProfileServiceDep,
) -> PlotProfileResponse:
    profile = await plot_profile_service.create(
        db_session,
        payload,
        user_id=current_user.id,
    )
    return _serialize(profile)


@router.patch("/{profile_id}", response_model=PlotProfileResponse)
async def update_plot_profile(
    profile_id: str,
    payload: PlotProfileUpdate,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    plot_profile_service: PlotProfileServiceDep,
) -> PlotProfileResponse:
    profile = await plot_profile_service.update(
        db_session,
        profile_id,
        payload,
        user_id=current_user.id,
    )
    return _serialize(profile)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plot_profile(
    profile_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    plot_profile_service: PlotProfileServiceDep,
) -> None:
    await plot_profile_service.delete(
        db_session,
        profile_id,
        user_id=current_user.id,
    )
