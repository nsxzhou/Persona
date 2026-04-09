from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.style_profiles import StyleProfileCreate, StyleProfileResponse
from app.services.style_profiles import StyleProfileService

router = APIRouter(prefix="/style-profiles", tags=["style-profiles"])


def _serialize(profile) -> StyleProfileResponse:
    return StyleProfileResponse.model_validate(profile)


@router.get("", response_model=list[StyleProfileResponse])
async def list_style_profiles(
    db_session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[StyleProfileResponse]:
    del current_user
    profiles = await StyleProfileService().list(db_session)
    return [_serialize(profile) for profile in profiles]


@router.get("/{profile_id}", response_model=StyleProfileResponse)
async def get_style_profile(
    profile_id: str,
    db_session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> StyleProfileResponse:
    del current_user
    profile = await StyleProfileService().get_or_404(db_session, profile_id)
    return _serialize(profile)


@router.post("", response_model=StyleProfileResponse, status_code=201)
async def create_style_profile(
    payload: StyleProfileCreate,
    db_session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> StyleProfileResponse:
    del current_user
    profile = await StyleProfileService().create(db_session, payload)
    await db_session.commit()
    return _serialize(profile)

