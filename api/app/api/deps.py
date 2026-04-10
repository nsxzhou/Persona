# 未来语法导入：支持前向引用的类型注解
from __future__ import annotations

# 导入FastAPI依赖注入系统
# Depends是FastAPI最强大也是最独特的功能
from fastapi import Depends, Request, Response

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import User
from app.db.session import get_db_session
from app.services.auth import AuthService
from app.services.style_analysis_jobs import StyleAnalysisJobService


def set_session_cookie(response: Response, raw_token: str) -> None:
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


def get_style_analysis_job_service() -> StyleAnalysisJobService:
    return StyleAnalysisJobService()
