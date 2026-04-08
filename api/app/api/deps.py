from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import User
from app.db.session import get_db_session
from app.services.auth import AuthService


async def get_current_user(
    request: Request,
    db_session: AsyncSession = Depends(get_db_session),
) -> User:
    settings = get_settings()
    auth_service = AuthService()
    return await auth_service.resolve_user_by_token(
        db_session,
        request.cookies.get(settings.session_cookie_name),
    )
