from __future__ import annotations

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from app.api.assemblers import build_plot_job_detail_response
from app.api.deps import CurrentUserDep, DbSessionDep, PlotAnalysisJobServiceDep
from app.core.config import get_settings
from app.core.domain_errors import UnprocessableEntityError
from app.schemas.plot_analysis_jobs import (
    PlotAnalysisJobListItemResponse,
    PlotAnalysisJobLogsResponse,
    PlotAnalysisJobResponse,
    PlotAnalysisJobStatusResponse,
    PlotAnalysisMeta,
    PlotAnalysisReportMarkdown,
    PlotSkeletonMarkdown,
    StoryEngineMarkdown,
)
from app.core.text_processing import clean_and_decode_upload

router = APIRouter(
    prefix="/plot-analysis-jobs",
    tags=["plot-analysis-jobs"],
)


@router.get("", response_model=list[PlotAnalysisJobListItemResponse])
async def list_plot_analysis_jobs(
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: PlotAnalysisJobServiceDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
) -> list[PlotAnalysisJobListItemResponse]:
    jobs = await job_service.list(
        db_session,
        user_id=current_user.id,
        offset=offset,
        limit=limit,
    )
    return [PlotAnalysisJobListItemResponse.model_validate(job) for job in jobs]


@router.get("/{job_id}", response_model=PlotAnalysisJobResponse)
async def get_plot_analysis_job(
    job_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: PlotAnalysisJobServiceDep,
) -> PlotAnalysisJobResponse:
    job = await job_service.get_detail_or_404(
        db_session,
        job_id,
        user_id=current_user.id,
    )
    return build_plot_job_detail_response(job)


@router.get("/{job_id}/status", response_model=PlotAnalysisJobStatusResponse)
async def get_plot_analysis_job_status(
    job_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: PlotAnalysisJobServiceDep,
) -> PlotAnalysisJobStatusResponse:
    return await job_service.get_status_or_404(
        db_session,
        job_id,
        user_id=current_user.id,
    )


@router.post("/{job_id}/resume", response_model=PlotAnalysisJobStatusResponse)
async def resume_plot_analysis_job(
    job_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: PlotAnalysisJobServiceDep,
) -> PlotAnalysisJobStatusResponse:
    return await job_service.resume(
        db_session,
        job_id,
        user_id=current_user.id,
    )


@router.post("/{job_id}/pause", response_model=PlotAnalysisJobStatusResponse)
async def pause_plot_analysis_job(
    job_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: PlotAnalysisJobServiceDep,
) -> PlotAnalysisJobStatusResponse:
    return await job_service.pause(
        db_session,
        job_id,
        user_id=current_user.id,
    )


@router.post("", response_model=PlotAnalysisJobListItemResponse, status_code=201)
async def create_plot_analysis_job(
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: PlotAnalysisJobServiceDep,
    plot_name: str = Form(...),
    provider_id: str = Form(...),
    model: str | None = Form(default=None),
    file: UploadFile = File(...),
) -> PlotAnalysisJobListItemResponse:
    if not (file.filename or "").lower().endswith(".txt"):
        raise UnprocessableEntityError("仅支持上传 .txt 样本文件")
    settings = get_settings()
    max_bytes = getattr(settings, "style_analysis_max_upload_bytes", 0) or 0
    job = await job_service.create(
        db_session,
        user_id=current_user.id,
        plot_name=plot_name,
        provider_id=provider_id,
        model=model,
        original_filename=file.filename or "",
        content_type=file.content_type,
        content_stream=clean_and_decode_upload(file, max_bytes=max_bytes),
    )
    return PlotAnalysisJobListItemResponse.model_validate(job)


@router.get("/{job_id}/logs", response_model=PlotAnalysisJobLogsResponse)
async def get_plot_analysis_job_logs(
    job_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: PlotAnalysisJobServiceDep,
    offset: int = Query(default=0, ge=0),
) -> PlotAnalysisJobLogsResponse:
    return await job_service.get_job_logs_or_404(
        db_session,
        job_id,
        user_id=current_user.id,
        offset=offset,
    )


@router.get("/{job_id}/analysis-meta", response_model=PlotAnalysisMeta)
async def get_plot_analysis_job_analysis_meta(
    job_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: PlotAnalysisJobServiceDep,
) -> PlotAnalysisMeta:
    return await job_service.get_analysis_meta_or_409(
        db_session,
        job_id,
        user_id=current_user.id,
    )


@router.get("/{job_id}/analysis-report", response_model=PlotAnalysisReportMarkdown)
async def get_plot_analysis_job_analysis_report(
    job_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: PlotAnalysisJobServiceDep,
) -> str:
    return await job_service.get_analysis_report_or_409(
        db_session,
        job_id,
        user_id=current_user.id,
    )


@router.get("/{job_id}/story-engine", response_model=StoryEngineMarkdown)
async def get_plot_analysis_job_story_engine(
    job_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: PlotAnalysisJobServiceDep,
) -> str:
    return await job_service.get_story_engine_or_409(
        db_session,
        job_id,
        user_id=current_user.id,
    )


@router.get("/{job_id}/plot-skeleton", response_model=PlotSkeletonMarkdown)
async def get_plot_analysis_job_plot_skeleton(
    job_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: PlotAnalysisJobServiceDep,
) -> str:
    return await job_service.get_plot_skeleton_or_409(
        db_session,
        job_id,
        user_id=current_user.id,
    )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plot_analysis_job(
    job_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: PlotAnalysisJobServiceDep,
) -> None:
    await job_service.delete(db_session, job_id, user_id=current_user.id)
