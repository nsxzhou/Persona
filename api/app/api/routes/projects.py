from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.projects import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.projects import ProjectService

router = APIRouter(
    prefix="/projects",
    tags=["projects"],
    dependencies=[Depends(get_current_user)],
)

@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    include_archived: bool = Query(default=False),
    db_session: AsyncSession = Depends(get_db_session),
) -> list[ProjectResponse]:
    projects = await ProjectService().list(db_session, include_archived=include_archived)
    return [ProjectResponse.model_validate(project) for project in projects]

@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    payload: ProjectCreate,
    db_session: AsyncSession = Depends(get_db_session),
) -> ProjectResponse:
    project = await ProjectService().create(db_session, payload)
    return ProjectResponse.model_validate(project)

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db_session: AsyncSession = Depends(get_db_session),
) -> ProjectResponse:
    project = await ProjectService().get_or_404(db_session, project_id)
    return ProjectResponse.model_validate(project)

@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    payload: ProjectUpdate,
    db_session: AsyncSession = Depends(get_db_session),
) -> ProjectResponse:
    project = await ProjectService().update(db_session, project_id, payload)
    return ProjectResponse.model_validate(project)

@router.post("/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(
    project_id: str,
    db_session: AsyncSession = Depends(get_db_session),
) -> ProjectResponse:
    project = await ProjectService().archive(db_session, project_id)
    return ProjectResponse.model_validate(project)

@router.post("/{project_id}/restore", response_model=ProjectResponse)
async def restore_project(
    project_id: str,
    db_session: AsyncSession = Depends(get_db_session),
) -> ProjectResponse:
    project = await ProjectService().restore(db_session, project_id)
    return ProjectResponse.model_validate(project)

