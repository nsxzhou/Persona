from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import CurrentUserDep, DbSessionDep, ProjectServiceDep
from app.schemas.projects import ProjectCreate, ProjectResponse, ProjectUpdate

router = APIRouter(
    prefix="/projects",
    tags=["projects"],
)

@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    _current_user: CurrentUserDep,
    db_session: DbSessionDep,
    project_service: ProjectServiceDep,
    include_archived: bool = Query(default=False),
) -> list[ProjectResponse]:
    projects = await project_service.list(db_session, include_archived=include_archived)
    return [ProjectResponse.model_validate(project) for project in projects]

@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    payload: ProjectCreate,
    _current_user: CurrentUserDep,
    db_session: DbSessionDep,
    project_service: ProjectServiceDep,
) -> ProjectResponse:
    project = await project_service.create(db_session, payload)
    return ProjectResponse.model_validate(project)

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    _current_user: CurrentUserDep,
    db_session: DbSessionDep,
    project_service: ProjectServiceDep,
) -> ProjectResponse:
    project = await project_service.get_or_404(db_session, project_id)
    return ProjectResponse.model_validate(project)

@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    payload: ProjectUpdate,
    _current_user: CurrentUserDep,
    db_session: DbSessionDep,
    project_service: ProjectServiceDep,
) -> ProjectResponse:
    project = await project_service.update(db_session, project_id, payload)
    return ProjectResponse.model_validate(project)

@router.post("/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(
    project_id: str,
    _current_user: CurrentUserDep,
    db_session: DbSessionDep,
    project_service: ProjectServiceDep,
) -> ProjectResponse:
    project = await project_service.archive(db_session, project_id)
    return ProjectResponse.model_validate(project)

@router.post("/{project_id}/restore", response_model=ProjectResponse)
async def restore_project(
    project_id: str,
    _current_user: CurrentUserDep,
    db_session: DbSessionDep,
    project_service: ProjectServiceDep,
) -> ProjectResponse:
    project = await project_service.restore(db_session, project_id)
    return ProjectResponse.model_validate(project)
