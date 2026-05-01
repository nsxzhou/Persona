from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.assemblers import (
    build_novel_workflow_detail_response,
    build_novel_workflow_status_response,
)
from app.api.deps import CurrentUserDep, DbSessionDep, NovelWorkflowServiceDep
from app.schemas.novel_workflows import (
    MarkdownArtifactResponse,
    NovelWorkflowCreateRequest,
    NovelWorkflowDecisionRequest,
    NovelWorkflowListItemResponse,
    NovelWorkflowLogsResponse,
    NovelWorkflowResponse,
    NovelWorkflowStatusResponse,
)

router = APIRouter(
    prefix="/novel-workflows",
    tags=["novel-workflows"],
)


@router.get("", response_model=list[NovelWorkflowListItemResponse])
async def list_novel_workflows(
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    workflow_service: NovelWorkflowServiceDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
) -> list[NovelWorkflowListItemResponse]:
    runs = await workflow_service.list(
        db_session,
        user_id=current_user.id,
        offset=offset,
        limit=limit,
    )
    return [NovelWorkflowListItemResponse.model_validate(run) for run in runs]


@router.post("", response_model=NovelWorkflowListItemResponse, status_code=201)
async def create_novel_workflow(
    payload: NovelWorkflowCreateRequest,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    workflow_service: NovelWorkflowServiceDep,
) -> NovelWorkflowListItemResponse:
    run = await workflow_service.create(
        db_session,
        payload,
        user_id=current_user.id,
    )
    return NovelWorkflowListItemResponse.model_validate(run)


@router.get("/{run_id}", response_model=NovelWorkflowResponse)
async def get_novel_workflow(
    run_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    workflow_service: NovelWorkflowServiceDep,
) -> NovelWorkflowResponse:
    run = await workflow_service.get_or_404(
        db_session,
        run_id,
        user_id=current_user.id,
    )
    return build_novel_workflow_detail_response(run)


@router.get("/{run_id}/status", response_model=NovelWorkflowStatusResponse)
async def get_novel_workflow_status(
    run_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    workflow_service: NovelWorkflowServiceDep,
) -> NovelWorkflowStatusResponse:
    run = await workflow_service.get_status_or_404(
        db_session,
        run_id,
        user_id=current_user.id,
    )
    return build_novel_workflow_status_response(run)


@router.post("/{run_id}/pause", response_model=NovelWorkflowStatusResponse)
async def pause_novel_workflow(
    run_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    workflow_service: NovelWorkflowServiceDep,
) -> NovelWorkflowStatusResponse:
    run = await workflow_service.pause(
        db_session,
        run_id,
        user_id=current_user.id,
    )
    return build_novel_workflow_status_response(run)


@router.post("/{run_id}/resume", response_model=NovelWorkflowStatusResponse)
async def resume_novel_workflow(
    run_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    workflow_service: NovelWorkflowServiceDep,
) -> NovelWorkflowStatusResponse:
    run = await workflow_service.resume(
        db_session,
        run_id,
        user_id=current_user.id,
    )
    return build_novel_workflow_status_response(run)


@router.post("/{run_id}/decision", response_model=NovelWorkflowStatusResponse)
async def submit_novel_workflow_decision(
    run_id: str,
    payload: NovelWorkflowDecisionRequest,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    workflow_service: NovelWorkflowServiceDep,
) -> NovelWorkflowStatusResponse:
    run = await workflow_service.submit_decision(
        db_session,
        run_id,
        payload,
        user_id=current_user.id,
    )
    return build_novel_workflow_status_response(run)


@router.get("/{run_id}/logs", response_model=NovelWorkflowLogsResponse)
async def get_novel_workflow_logs(
    run_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    workflow_service: NovelWorkflowServiceDep,
    offset: int = Query(default=0, ge=0),
) -> NovelWorkflowLogsResponse:
    return await workflow_service.get_job_logs_or_404(
        db_session,
        run_id,
        user_id=current_user.id,
        offset=offset,
    )


@router.get("/{run_id}/artifacts/{artifact_name}", response_model=MarkdownArtifactResponse)
async def get_novel_workflow_artifact(
    run_id: str,
    artifact_name: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    workflow_service: NovelWorkflowServiceDep,
) -> str:
    return await workflow_service.get_artifact_or_404(
        db_session,
        run_id,
        artifact_name,
        user_id=current_user.id,
    )
