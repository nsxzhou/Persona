from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.auth import LoginRequest, UserResponse
from app.services.auth import AuthService

router = APIRouter(tags=["auth"])


def _set_session_cookie(response: Response, raw_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )


@router.post("/login", response_model=UserResponse)
async def login(payload: LoginRequest, response: Response, db_session: AsyncSession = Depends(get_db_session)) -> UserResponse:
    auth_service = AuthService()
    if not await auth_service.is_initialized(db_session):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="系统尚未初始化")

    user = await auth_service.authenticate(db_session, payload.username, payload.password)
    _, raw_token = await auth_service.create_session(db_session, user)
    await db_session.commit()
    _set_session_cookie(response, raw_token)
    return UserResponse.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    db_session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    del current_user
    settings = get_settings()
    raw_token = request.cookies.get(settings.session_cookie_name)
    await AuthService().delete_session(db_session, raw_token)
    await db_session.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(settings.session_cookie_name, path="/")
    return response


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
