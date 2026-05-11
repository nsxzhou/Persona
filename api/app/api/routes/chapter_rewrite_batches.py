from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.api.deps import ChapterRewriteBatchServiceDep, CurrentUserDep, DbSessionDep
from app.schemas.chapter_rewrite_batches import (
    ChapterRewriteBatchApplyItemResponse,
    ChapterRewriteBatchApplyResponse,
    ChapterRewriteBatchCreateRequest,
    ChapterRewriteBatchItemLogsResponse,
    ChapterRewriteBatchListItemResponse,
    ChapterRewriteBatchMarkdownArtifactResponse,
    ChapterRewriteBatchResponse,
)
from app.services.chapter_rewrite_batches import ChapterRewriteBatchService


router = APIRouter(
    prefix="/chapter-rewrite-batches",
    tags=["chapter-rewrite-batches"],
)


def _batch_response(
    service: ChapterRewriteBatchService,
    batch,
) -> ChapterRewriteBatchResponse:
    return ChapterRewriteBatchResponse.model_validate(service.enrich_batch(batch))


@router.post("", response_model=ChapterRewriteBatchResponse, status_code=status.HTTP_201_CREATED)
async def create_chapter_rewrite_batch(
    payload: ChapterRewriteBatchCreateRequest,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    batch_service: ChapterRewriteBatchServiceDep,
) -> ChapterRewriteBatchResponse:
    batch = await batch_service.create(db_session, payload, user_id=current_user.id)
    return _batch_response(batch_service, batch)


@router.get("", response_model=list[ChapterRewriteBatchListItemResponse])
async def list_chapter_rewrite_batches(
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    batch_service: ChapterRewriteBatchServiceDep,
    project_id: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[ChapterRewriteBatchListItemResponse]:
    batches = await batch_service.list(
        db_session,
        user_id=current_user.id,
        project_id=project_id,
        offset=offset,
        limit=limit,
    )
    return [
        ChapterRewriteBatchListItemResponse.model_validate(batch_service.enrich_batch(batch))
        for batch in batches
    ]


@router.get("/{batch_id}", response_model=ChapterRewriteBatchResponse)
async def get_chapter_rewrite_batch(
    batch_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    batch_service: ChapterRewriteBatchServiceDep,
) -> ChapterRewriteBatchResponse:
    batch = await batch_service.get_or_404(db_session, batch_id, user_id=current_user.id)
    return _batch_response(batch_service, batch)


@router.get(
    "/{batch_id}/items/{item_id}/logs",
    response_model=ChapterRewriteBatchItemLogsResponse,
)
async def get_chapter_rewrite_batch_item_logs(
    batch_id: str,
    item_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    batch_service: ChapterRewriteBatchServiceDep,
    offset: int = Query(default=0, ge=0),
) -> ChapterRewriteBatchItemLogsResponse:
    return await batch_service.get_item_logs_or_404(
        db_session,
        batch_id,
        item_id,
        user_id=current_user.id,
        offset=offset,
    )


@router.get(
    "/{batch_id}/items/{item_id}/artifact",
    response_model=ChapterRewriteBatchMarkdownArtifactResponse,
)
async def get_chapter_rewrite_batch_item_artifact(
    batch_id: str,
    item_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    batch_service: ChapterRewriteBatchServiceDep,
) -> str:
    return await batch_service.get_item_artifact_or_404(
        db_session,
        batch_id,
        item_id,
        user_id=current_user.id,
    )


@router.post(
    "/{batch_id}/items/{item_id}/apply",
    response_model=ChapterRewriteBatchApplyItemResponse,
)
async def apply_chapter_rewrite_batch_item(
    batch_id: str,
    item_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    batch_service: ChapterRewriteBatchServiceDep,
) -> ChapterRewriteBatchApplyItemResponse:
    return await batch_service.apply_item(
        db_session,
        batch_id,
        item_id,
        user_id=current_user.id,
    )


@router.post("/{batch_id}/apply", response_model=ChapterRewriteBatchApplyResponse)
async def apply_chapter_rewrite_batch(
    batch_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    batch_service: ChapterRewriteBatchServiceDep,
) -> ChapterRewriteBatchApplyResponse:
    return await batch_service.apply_batch(db_session, batch_id, user_id=current_user.id)
