from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.style_analysis_jobs import StyleAnalysisJobResponse
from app.services.style_analysis_jobs import StyleAnalysisJobService, build_job_result_bundle

router = APIRouter(prefix="/style-analysis-jobs", tags=["style-analysis-jobs"])


def _serialize(job) -> StyleAnalysisJobResponse:
    analysis_meta, analysis_report, style_summary, prompt_pack = build_job_result_bundle(job)
    return StyleAnalysisJobResponse(
        id=job.id,
        style_name=job.style_name,
        provider_id=job.provider_id,
        model_name=job.model_name,
        status=job.status,
        stage=job.stage,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
        updated_at=job.updated_at,
        provider=job.provider,
        sample_file=job.sample_file,
        style_profile_id=job.style_profile.id if job.style_profile else None,
        analysis_meta=analysis_meta,
        analysis_report=analysis_report,
        style_summary=style_summary,
        prompt_pack=prompt_pack,
    )


@router.get("", response_model=list[StyleAnalysisJobResponse])
async def list_style_analysis_jobs(
    db_session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[StyleAnalysisJobResponse]:
    del current_user
    jobs = await StyleAnalysisJobService().list(db_session)
    return [_serialize(job) for job in jobs]


@router.get("/{job_id}", response_model=StyleAnalysisJobResponse)
async def get_style_analysis_job(
    job_id: str,
    db_session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> StyleAnalysisJobResponse:
    del current_user
    job = await StyleAnalysisJobService().get_or_404(db_session, job_id)
    return _serialize(job)


@router.post("", response_model=StyleAnalysisJobResponse, status_code=201)
async def create_style_analysis_job(
    style_name: str = Form(...),
    provider_id: str = Form(...),
    model: str | None = Form(default=None),
    file: UploadFile = File(...),
    db_session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> StyleAnalysisJobResponse:
    del current_user
    job = await StyleAnalysisJobService().create(
        db_session,
        style_name=style_name,
        provider_id=provider_id,
        model=model,
        upload_file=file,
    )
    await db_session.commit()
    return _serialize(job)
