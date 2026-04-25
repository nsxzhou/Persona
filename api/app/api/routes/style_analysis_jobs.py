from __future__ import annotations

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from app.api.deps import CurrentUserDep, DbSessionDep, StyleAnalysisJobServiceDep
from app.core.domain_errors import UnprocessableEntityError
from app.api.assemblers import build_job_detail_response
from app.core.config import get_settings
from app.schemas.style_analysis_jobs import (
    AnalysisReportMarkdown,
    AnalysisMeta,
    StyleAnalysisJobLogsResponse,
    StyleAnalysisJobListItemResponse,
    StyleAnalysisJobResponse,
    StyleAnalysisJobStatusResponse,
    VoiceProfileMarkdown,
)
from app.services.style_analysis_text import clean_and_decode_upload

router = APIRouter(
    prefix="/style-analysis-jobs",
    tags=["style-analysis-jobs"],
)

@router.get("", response_model=list[StyleAnalysisJobListItemResponse])
async def list_style_analysis_jobs(
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: StyleAnalysisJobServiceDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
) -> list[StyleAnalysisJobListItemResponse]:
    jobs = await job_service.list(
        db_session,
        user_id=current_user.id,
        offset=offset,
        limit=limit,
    )
    return [StyleAnalysisJobListItemResponse.model_validate(job) for job in jobs]

@router.get("/{job_id}", response_model=StyleAnalysisJobResponse)
async def get_style_analysis_job(
    job_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: StyleAnalysisJobServiceDep,
) -> StyleAnalysisJobResponse:
    job = await job_service.get_detail_or_404(
        db_session,
        job_id,
        user_id=current_user.id,
    )
    return build_job_detail_response(job)


@router.get("/{job_id}/status", response_model=StyleAnalysisJobStatusResponse)
async def get_style_analysis_job_status(
    job_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: StyleAnalysisJobServiceDep,
) -> StyleAnalysisJobStatusResponse:
    return await job_service.get_status_or_404(
        db_session,
        job_id,
        user_id=current_user.id,
    )

@router.post("/{job_id}/resume", response_model=StyleAnalysisJobStatusResponse)
async def resume_style_analysis_job(
    job_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: StyleAnalysisJobServiceDep,
) -> StyleAnalysisJobStatusResponse:
    return await job_service.resume(
        db_session,
        job_id,
        user_id=current_user.id,
    )

@router.post("/{job_id}/pause", response_model=StyleAnalysisJobStatusResponse)
async def pause_style_analysis_job(
    job_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: StyleAnalysisJobServiceDep,
) -> StyleAnalysisJobStatusResponse:
    return await job_service.pause(
        db_session,
        job_id,
        user_id=current_user.id,
    )


@router.post("", response_model=StyleAnalysisJobListItemResponse, status_code=201)
async def create_style_analysis_job(
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: StyleAnalysisJobServiceDep,
    style_name: str = Form(...),
    provider_id: str = Form(...),
    model: str | None = Form(default=None),
    file: UploadFile = File(...),
) -> StyleAnalysisJobListItemResponse:
    if not (file.filename or "").lower().endswith(".txt"):
        raise UnprocessableEntityError("仅支持上传 .txt 样本文件")
    settings = get_settings()
    max_bytes = getattr(settings, "style_analysis_max_upload_bytes", 0) or 0
    job = await job_service.create(
        db_session,
        user_id=current_user.id,
        style_name=style_name,
        provider_id=provider_id,
        model=model,
        original_filename=file.filename or "",
        content_type=file.content_type,
        content_stream=clean_and_decode_upload(file, max_bytes=max_bytes),
    )
    return StyleAnalysisJobListItemResponse.model_validate(job)

@router.get("/{job_id}/logs", response_model=StyleAnalysisJobLogsResponse)
async def get_style_analysis_job_logs(
    job_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: StyleAnalysisJobServiceDep,
    offset: int = Query(default=0, ge=0),
) -> StyleAnalysisJobLogsResponse:
    return await job_service.get_job_logs_or_404(
        db_session,
        job_id,
        user_id=current_user.id,
        offset=offset,
    )

@router.get("/{job_id}/analysis-meta", response_model=AnalysisMeta)
async def get_style_analysis_job_analysis_meta(
    job_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: StyleAnalysisJobServiceDep,
) -> AnalysisMeta:
    return await job_service.get_analysis_meta_or_409(
        db_session,
        job_id,
        user_id=current_user.id,
    )


@router.get("/{job_id}/analysis-report", response_model=AnalysisReportMarkdown)
async def get_style_analysis_job_analysis_report(
    job_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: StyleAnalysisJobServiceDep,
) -> str:
    return await job_service.get_analysis_report_or_409(
        db_session,
        job_id,
        user_id=current_user.id,
    )


@router.get("/{job_id}/voice-profile", response_model=VoiceProfileMarkdown)
async def get_style_analysis_job_voice_profile(
    job_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: StyleAnalysisJobServiceDep,
) -> str:
    return await job_service.get_voice_profile_or_409(
        db_session,
        job_id,
        user_id=current_user.id,
    )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_style_analysis_job(
    job_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: StyleAnalysisJobServiceDep,
) -> None:
    await job_service.delete(db_session, job_id, user_id=current_user.id)
