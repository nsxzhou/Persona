from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request, Response

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import User
from app.db.session import get_db_session
from app.services.auth import AuthService
from app.services.checkpointer_factory import PlotAnalysisCheckpointerFactory
from app.services.export import ProjectExportService
from app.services.novel_workflows import NovelWorkflowService
from app.services.plot_analysis_jobs import PlotAnalysisJobService
from app.services.plot_analysis_storage import PlotAnalysisStorageService
from app.services.plot_profiles import PlotProfileService
from app.services.project_chapters import ProjectChapterService
from app.services.projects import ProjectService
from app.services.provider_configs import ProviderConfigService
from app.services.setup import SetupService
from app.services.style_analysis_checkpointer import StyleAnalysisCheckpointerFactory
from app.services.style_analysis_jobs import StyleAnalysisJobService
from app.services.style_analysis_storage import StyleAnalysisStorageService
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


def get_project_chapter_service(
    project_service: ProjectServiceDep,
) -> ProjectChapterService:
    return ProjectChapterService(project_service=project_service)


ProjectChapterServiceDep = Annotated[
    ProjectChapterService,
    Depends(get_project_chapter_service),
]


def get_setup_service(
    auth_service: AuthServiceDep,
    provider_service: ProviderConfigServiceDep,
) -> SetupService:
    return SetupService(
        auth_service=auth_service,
        provider_service=provider_service,
    )


SetupServiceDep = Annotated[SetupService, Depends(get_setup_service)]


def get_project_export_service(
    project_service: ProjectServiceDep,
    project_chapter_service: ProjectChapterServiceDep,
) -> ProjectExportService:
    return ProjectExportService(
        project_service=project_service,
        project_chapter_service=project_chapter_service,
    )


ProjectExportServiceDep = Annotated[
    ProjectExportService,
    Depends(get_project_export_service),
]


def get_style_analysis_job_service(
    provider_service: ProviderConfigServiceDep,
) -> StyleAnalysisJobService:
    return StyleAnalysisJobService(
        provider_service=provider_service,
        storage_service=StyleAnalysisStorageService(),
        checkpointer_factory=StyleAnalysisCheckpointerFactory(),
    )


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


def get_plot_analysis_job_service(
    provider_service: ProviderConfigServiceDep,
) -> PlotAnalysisJobService:
    return PlotAnalysisJobService(
        provider_service=provider_service,
        storage_service=PlotAnalysisStorageService(),
        checkpointer_factory=PlotAnalysisCheckpointerFactory(),
    )


PlotAnalysisJobServiceDep = Annotated[
    PlotAnalysisJobService,
    Depends(get_plot_analysis_job_service),
]


def get_plot_profile_service() -> PlotProfileService:
    return PlotProfileService()


PlotProfileServiceDep = Annotated[
    PlotProfileService,
    Depends(get_plot_profile_service),
]


def get_novel_workflow_service(
    project_service: ProjectServiceDep,
    project_chapter_service: ProjectChapterServiceDep,
    provider_service: ProviderConfigServiceDep,
) -> NovelWorkflowService:
    return NovelWorkflowService(
        project_service=project_service,
        project_chapter_service=project_chapter_service,
        provider_service=provider_service,
    )


NovelWorkflowServiceDep = Annotated[
    NovelWorkflowService,
    Depends(get_novel_workflow_service),
]
