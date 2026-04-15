from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request, Response

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import User
from app.db.session import get_db_session
from app.services.auth import AuthService
from app.services.editor import EditorService
from app.services.llm_provider import LLMProviderService
from app.services.projects import ProjectService
from app.services.provider_configs import ProviderConfigService
from app.services.style_analysis_jobs import StyleAnalysisJobService
from app.services.style_profiles import StyleProfileService

DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


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


def get_auth_service() -> AuthService:
    return AuthService()


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


async def get_current_user(
    request: Request,
    db_session: DbSessionDep,
    auth_service: AuthServiceDep,
) -> User:
    settings = get_settings()
    return await auth_service.resolve_user_by_token(
        db_session,
        request.cookies.get(settings.session_cookie_name),
    )


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def get_provider_config_service() -> ProviderConfigService:
    return ProviderConfigService()


ProviderConfigServiceDep = Annotated[
    ProviderConfigService,
    Depends(get_provider_config_service),
]


def get_project_service(
    provider_service: ProviderConfigServiceDep,
) -> ProjectService:
    return ProjectService(provider_service=provider_service)


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]


def get_style_analysis_job_service() -> StyleAnalysisJobService:
    return StyleAnalysisJobService()


StyleAnalysisJobServiceDep = Annotated[
    StyleAnalysisJobService,
    Depends(get_style_analysis_job_service),
]


def get_style_profile_service() -> StyleProfileService:
    return StyleProfileService()


StyleProfileServiceDep = Annotated[
    StyleProfileService,
    Depends(get_style_profile_service),
]


def get_llm_provider_service() -> LLMProviderService:
    return LLMProviderService()


LLMProviderServiceDep = Annotated[
    LLMProviderService,
    Depends(get_llm_provider_service),
]


def get_editor_service(
    llm_service: LLMProviderServiceDep,
    project_service: ProjectServiceDep,
    style_profile_service: StyleProfileServiceDep,
    provider_config_service: ProviderConfigServiceDep,
) -> EditorService:
    return EditorService(
        llm_service=llm_service,
        project_service=project_service,
        style_profile_service=style_profile_service,
        provider_config_service=provider_config_service,
    )


EditorServiceDep = Annotated[EditorService, Depends(get_editor_service)]
