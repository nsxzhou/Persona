from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import (
    CurrentUserDep,
    DbSessionDep,
    ProjectChapterServiceDep,
)
from app.schemas.project_chapters import ProjectChapterResponse, ProjectChapterUpdate

router = APIRouter(
    prefix="/projects",
    tags=["project-chapters"],
)


@router.get("/{project_id}/chapters", response_model=list[ProjectChapterResponse])
async def list_project_chapters(
    project_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    chapter_service: ProjectChapterServiceDep,
) -> list[ProjectChapterResponse]:
    chapters = await chapter_service.list(
        db_session, project_id, user_id=current_user.id,
    )
    return [ProjectChapterResponse.model_validate(chapter) for chapter in chapters]


@router.post(
    "/{project_id}/chapters/sync-outline",
    response_model=list[ProjectChapterResponse],
)
async def sync_project_chapters_from_outline(
    project_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    chapter_service: ProjectChapterServiceDep,
) -> list[ProjectChapterResponse]:
    chapters = await chapter_service.sync_outline(
        db_session, project_id, user_id=current_user.id,
    )
    return [ProjectChapterResponse.model_validate(chapter) for chapter in chapters]


@router.patch(
    "/{project_id}/chapters/{chapter_id}",
    response_model=ProjectChapterResponse,
)
async def update_project_chapter(
    project_id: str,
    chapter_id: str,
    payload: ProjectChapterUpdate,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    chapter_service: ProjectChapterServiceDep,
) -> ProjectChapterResponse:
    chapter = await chapter_service.update(
        db_session,
        project_id,
        chapter_id,
        payload,
        user_id=current_user.id,
    )
    return ProjectChapterResponse.model_validate(chapter)
