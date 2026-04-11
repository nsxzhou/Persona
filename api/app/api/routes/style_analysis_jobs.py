from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from app.api.deps import CurrentUserDep, DbSessionDep, StyleAnalysisJobServiceDep
from app.schemas.style_analysis_jobs import (
    AnalysisMeta,
    AnalysisReport,
    PromptPack,
    StyleAnalysisJobListItemResponse,
    StyleAnalysisJobResponse,
    StyleSummary,
)
from app.services.style_analysis_jobs import StyleAnalysisJobService, build_job_detail_response

router = APIRouter(
    prefix="/style-analysis-jobs",
    tags=["style-analysis-jobs"],
)

@router.get("", response_model=list[StyleAnalysisJobListItemResponse])
async def list_style_analysis_jobs(
    _current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: StyleAnalysisJobServiceDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
) -> list[StyleAnalysisJobListItemResponse]:
    jobs = await job_service.list(db_session, offset=offset, limit=limit)
    return [StyleAnalysisJobListItemResponse.model_validate(job) for job in jobs]

@router.get("/{job_id}", response_model=StyleAnalysisJobResponse)
async def get_style_analysis_job(
    job_id: str,
    _current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: StyleAnalysisJobServiceDep,
) -> StyleAnalysisJobResponse:
    job = await job_service.get_or_404(db_session, job_id, include_payloads=True)
    return build_job_detail_response(job)

@router.post("", response_model=StyleAnalysisJobListItemResponse, status_code=201)
async def create_style_analysis_job(
    _current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: StyleAnalysisJobServiceDep,
    style_name: str = Form(...),
    provider_id: str = Form(...),
    model: str | None = Form(default=None),
    file: UploadFile = File(...),
) -> StyleAnalysisJobListItemResponse:
    if not (file.filename or "").lower().endswith(".txt"):
        raise HTTPException(status_code=422, detail="仅支持上传 .txt 样本文件")
    job = await job_service.create(
        db_session,
        style_name=style_name,
        provider_id=provider_id,
        model=model,
        upload_file=file,
    )
    # 我们也可以把下面这行省略，因为下面我们会去修改 service.create 让他返回完整的对象，但是现在先保留
    job = await job_service.get_or_404(db_session, job.id, include_payloads=False)
    return StyleAnalysisJobListItemResponse.model_validate(job)


@router.get("/{job_id}/analysis-meta", response_model=AnalysisMeta)
async def get_style_analysis_job_analysis_meta(
    job_id: str,
    _current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: StyleAnalysisJobServiceDep,
) -> AnalysisMeta:
    return await job_service.get_analysis_meta_or_409(db_session, job_id)


@router.get("/{job_id}/analysis-report", response_model=AnalysisReport)
async def get_style_analysis_job_analysis_report(
    job_id: str,
    _current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: StyleAnalysisJobServiceDep,
) -> AnalysisReport:
    return await job_service.get_analysis_report_or_409(db_session, job_id)


@router.get("/{job_id}/style-summary", response_model=StyleSummary)
async def get_style_analysis_job_style_summary(
    job_id: str,
    _current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: StyleAnalysisJobServiceDep,
) -> StyleSummary:
    return await job_service.get_style_summary_or_409(db_session, job_id)


@router.get("/{job_id}/prompt-pack", response_model=PromptPack)
async def get_style_analysis_job_prompt_pack(
    job_id: str,
    _current_user: CurrentUserDep,
    db_session: DbSessionDep,
    job_service: StyleAnalysisJobServiceDep,
) -> PromptPack:
    return await job_service.get_prompt_pack_or_409(db_session, job_id)
