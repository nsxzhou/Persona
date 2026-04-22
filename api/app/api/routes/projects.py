from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Query, status
from fastapi.responses import StreamingResponse

from app.api.deps import (
    CurrentUserDep,
    DbSessionDep,
    ProjectServiceDep,
    ProjectChapterServiceDep,
)
from app.schemas.projects import (
    ProjectCreate,
    ProjectResponse,
    ProjectSummaryResponse,
    ProjectUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/projects",
    tags=["projects"],
)


@router.get("", response_model=list[ProjectSummaryResponse])
async def list_projects(
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    project_service: ProjectServiceDep,
    include_archived: bool = Query(default=False),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
) -> list[ProjectSummaryResponse]:
    projects = await project_service.list(
        db_session,
        user_id=current_user.id,
        include_archived=include_archived,
        offset=offset,
        limit=limit,
    )
    return [ProjectSummaryResponse.model_validate(project) for project in projects]


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    payload: ProjectCreate,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    project_service: ProjectServiceDep,
) -> ProjectResponse:
    project = await project_service.create(
        db_session,
        payload,
        user_id=current_user.id,
    )
    return ProjectResponse.model_validate(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    project_service: ProjectServiceDep,
) -> ProjectResponse:
    project = await project_service.get_or_404(
        db_session,
        project_id,
        user_id=current_user.id,
    )
    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    payload: ProjectUpdate,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    project_service: ProjectServiceDep,
) -> ProjectResponse:
    project = await project_service.update(
        db_session,
        project_id,
        payload,
        user_id=current_user.id,
    )
    return ProjectResponse.model_validate(project)


@router.post("/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(
    project_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    project_service: ProjectServiceDep,
) -> ProjectResponse:
    project = await project_service.archive(
        db_session,
        project_id,
        user_id=current_user.id,
    )
    return ProjectResponse.model_validate(project)


@router.post("/{project_id}/restore", response_model=ProjectResponse)
async def restore_project(
    project_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    project_service: ProjectServiceDep,
) -> ProjectResponse:
    project = await project_service.restore(
        db_session,
        project_id,
        user_id=current_user.id,
    )
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    project_service: ProjectServiceDep,
) -> None:
    await project_service.delete(
        db_session,
        project_id,
        user_id=current_user.id,
    )


@router.get("/{project_id}/export")
async def export_project(
    project_id: str,
    format: Literal["txt", "epub"],
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    project_service: ProjectServiceDep,
    project_chapter_service: ProjectChapterServiceDep,
) -> StreamingResponse:
    from app.services.export import ExportService

    project = await project_service.get_or_404(
        db_session,
        project_id,
        user_id=current_user.id,
    )
    chapters = await project_chapter_service.list(
        db_session, project_id, user_id=current_user.id
    )

    return ExportService.build_export_response(project, chapters, format)
