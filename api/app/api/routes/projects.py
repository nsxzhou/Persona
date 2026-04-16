from __future__ import annotations

import logging

from fastapi import APIRouter, Query, status
from fastapi.responses import StreamingResponse

from app.api.deps import (
    CurrentUserDep,
    DbSessionDep,
    EditorServiceDep,
    ProjectChapterServiceDep,
    ProjectServiceDep,
)
from app.api.sse import sse_response
from app.schemas.editor import (
    BeatExpandRequest,
    BeatGenerateRequest,
    BeatGenerateResponse,
    BibleUpdateRequest,
    BibleUpdateResponse,
    ConceptGenerateRequest,
    ConceptGenerateResponse,
    EditorCompletionRequest,
    SectionGenerateRequest,
    VolumeChaptersRequest,
)
from app.schemas.project_chapters import ProjectChapterResponse, ProjectChapterUpdate
from app.schemas.projects import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/projects",
    tags=["projects"],
)

@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    project_service: ProjectServiceDep,
    include_archived: bool = Query(default=False),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
) -> list[ProjectResponse]:
    projects = await project_service.list(
        db_session,
        user_id=current_user.id,
        include_archived=include_archived,
        offset=offset,
        limit=limit,
    )
    return [ProjectResponse.model_validate(project) for project in projects]

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


@router.post("/generate-concepts", response_model=ConceptGenerateResponse)
async def generate_concepts(
    payload: ConceptGenerateRequest,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    editor_service: EditorServiceDep,
) -> ConceptGenerateResponse:
    concepts = await editor_service.generate_concepts(
        db_session, current_user.id, payload,
    )
    return ConceptGenerateResponse(concepts=concepts)


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


@router.post("/{project_id}/chapters/sync-outline", response_model=list[ProjectChapterResponse])
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


@router.patch("/{project_id}/chapters/{chapter_id}", response_model=ProjectChapterResponse)
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
        payload.content,
        user_id=current_user.id,
    )
    return ProjectChapterResponse.model_validate(chapter)


# --------------------------------------------------------------------------- #
#  AI editor endpoints — thin handlers delegating to EditorService             #
# --------------------------------------------------------------------------- #

@router.post("/{project_id}/editor/complete")
async def editor_complete(
    project_id: str,
    payload: EditorCompletionRequest,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    editor_service: EditorServiceDep,
) -> StreamingResponse:
    gen = await editor_service.stream_completion(
        db_session, project_id, current_user.id, payload,
    )
    return sse_response(gen, error_log_message="AI 续写异常")


@router.post("/{project_id}/editor/generate-section")
async def generate_section(
    project_id: str,
    payload: SectionGenerateRequest,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    editor_service: EditorServiceDep,
) -> StreamingResponse:
    gen = await editor_service.stream_section_generation(
        db_session, project_id, current_user.id, payload,
    )
    return sse_response(gen, error_log_message="区块 AI 生成异常")


@router.post("/{project_id}/editor/propose-bible-update", response_model=BibleUpdateResponse)
async def propose_bible_update(
    project_id: str,
    payload: BibleUpdateRequest,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    editor_service: EditorServiceDep,
) -> BibleUpdateResponse:
    proposed_state, proposed_threads = await editor_service.propose_bible_update(
        db_session, project_id, current_user.id, payload,
    )
    return BibleUpdateResponse(
        proposed_runtime_state=proposed_state,
        proposed_runtime_threads=proposed_threads,
    )


@router.post("/{project_id}/editor/generate-beats", response_model=BeatGenerateResponse)
async def generate_beats(
    project_id: str,
    payload: BeatGenerateRequest,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    editor_service: EditorServiceDep,
) -> BeatGenerateResponse:
    beats = await editor_service.generate_beats(
        db_session, project_id, current_user.id, payload,
    )
    return BeatGenerateResponse(beats=beats)


@router.post("/{project_id}/editor/expand-beat")
async def expand_beat(
    project_id: str,
    payload: BeatExpandRequest,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    editor_service: EditorServiceDep,
) -> StreamingResponse:
    gen = await editor_service.stream_beat_expansion(
        db_session, project_id, current_user.id, payload,
    )
    return sse_response(gen, error_log_message="节拍展开异常")


@router.post("/{project_id}/editor/generate-volumes")
async def generate_volumes(
    project_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    editor_service: EditorServiceDep,
) -> StreamingResponse:
    gen = await editor_service.stream_volume_generation(
        db_session, project_id, current_user.id,
    )
    return sse_response(gen, error_log_message="分卷结构生成异常")


@router.post("/{project_id}/editor/generate-volume-chapters")
async def generate_volume_chapters(
    project_id: str,
    payload: VolumeChaptersRequest,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    editor_service: EditorServiceDep,
) -> StreamingResponse:
    gen = await editor_service.stream_volume_chapters_generation(
        db_session, project_id, current_user.id, payload,
    )
    return sse_response(gen, error_log_message="卷章节生成异常")
