from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.api.assemblers import build_novel_workflow_status_response
from app.api.deps import CurrentUserDep, DbSessionDep, NovelChapterRewriteJobServiceDep
from app.schemas.novel_chapter_rewrite_jobs import (
    NovelChapterRewriteJobApplyResponse,
    NovelChapterRewriteJobCreateRequest,
    NovelChapterRewriteJobLogsResponse,
    NovelChapterRewriteJobMarkdownArtifactResponse,
    NovelChapterRewriteJobResponse,
    NovelChapterRewriteJobStatusResponse,
)
from app.schemas.project_chapters import ProjectChapterResponse

router = APIRouter(
    prefix="/novel-chapter-rewrite-jobs",
    tags=["novel-chapter-rewrite-jobs"],
)


@router.post("", response_model=NovelChapterRewriteJobResponse, status_code=201)
async def create_novel_chapter_rewrite_job(
    payload: NovelChapterRewriteJobCreateRequest,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: NovelChapterRewriteJobServiceDep,
) -> NovelChapterRewriteJobResponse:
    run = await job_service.create(db_session, payload, user_id=current_user.id)
    return NovelChapterRewriteJobResponse.model_validate(run)


@router.get("/{job_id}/status", response_model=NovelChapterRewriteJobStatusResponse)
async def get_novel_chapter_rewrite_job_status(
    job_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: NovelChapterRewriteJobServiceDep,
) -> NovelChapterRewriteJobStatusResponse:
    run = await job_service.get_status_or_404(
        db_session,
        job_id,
        user_id=current_user.id,
    )
    return build_novel_workflow_status_response(run)


@router.get("/{job_id}/logs", response_model=NovelChapterRewriteJobLogsResponse)
async def get_novel_chapter_rewrite_job_logs(
    job_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: NovelChapterRewriteJobServiceDep,
    offset: int = Query(default=0, ge=0),
) -> NovelChapterRewriteJobLogsResponse:
    return await job_service.get_logs_or_404(
        db_session,
        job_id,
        user_id=current_user.id,
        offset=offset,
    )


@router.get("/{job_id}/artifact", response_model=NovelChapterRewriteJobMarkdownArtifactResponse)
async def get_novel_chapter_rewrite_job_artifact(
    job_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: NovelChapterRewriteJobServiceDep,
) -> str:
    return await job_service.get_artifact_or_404(
        db_session,
        job_id,
        user_id=current_user.id,
    )


@router.post("/{job_id}/apply", response_model=NovelChapterRewriteJobApplyResponse)
async def apply_novel_chapter_rewrite_job(
    job_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: NovelChapterRewriteJobServiceDep,
) -> NovelChapterRewriteJobApplyResponse:
    chapter = await job_service.apply_artifact(
        db_session,
        job_id,
        user_id=current_user.id,
    )
    return NovelChapterRewriteJobApplyResponse(
        chapter=ProjectChapterResponse.model_validate(chapter)
    )
