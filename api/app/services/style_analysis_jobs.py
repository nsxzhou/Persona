from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import StyleAnalysisJob, StyleProfile
from app.db.repositories.style_analysis_jobs import StyleAnalysisJobRepository
from app.schemas.style_analysis_jobs import (
    AnalysisMeta,
    AnalysisReport,
    PromptPack,
    STYLE_ANALYSIS_JOB_STAGE_PREPARING_INPUT,
    STYLE_ANALYSIS_JOB_STATUS_FAILED,
    STYLE_ANALYSIS_JOB_STATUS_PENDING,
    STYLE_ANALYSIS_JOB_STATUS_RUNNING,
    STYLE_ANALYSIS_JOB_STATUS_SUCCEEDED,
    StyleAnalysisJobResponse,
    StyleProfileEmbeddedResponse,
    StyleSummary,
)
from app.services.provider_configs import ProviderConfigService
from app.services.style_analysis_pipeline import StyleAnalysisPipelineResult
from app.services.style_analysis_storage import StyleAnalysisStorageService


def build_job_result_bundle(job: StyleAnalysisJob) -> tuple[
    AnalysisMeta | None,
    AnalysisReport | None,
    StyleSummary | None,
    PromptPack | None,
]:
    if (
        job.analysis_meta_payload
        and job.analysis_report_payload
        and job.style_summary_payload
        and job.prompt_pack_payload
    ):
        return (
            AnalysisMeta.model_validate(job.analysis_meta_payload),
            AnalysisReport.model_validate(job.analysis_report_payload),
            StyleSummary.model_validate(job.style_summary_payload),
            PromptPack.model_validate(job.prompt_pack_payload),
        )

    return None, None, None, None


def build_profile_result_bundle(profile: StyleProfile) -> tuple[AnalysisReport, StyleSummary, PromptPack]:
    return (
        AnalysisReport.model_validate(profile.analysis_report_payload),
        StyleSummary.model_validate(profile.style_summary_payload),
        PromptPack.model_validate(profile.prompt_pack_payload),
    )


def build_style_profile_embedded_response(
    profile: StyleProfile | None,
) -> StyleProfileEmbeddedResponse | None:
    if profile is None:
        return None
    analysis_report, style_summary, prompt_pack = build_profile_result_bundle(profile)
    return StyleProfileEmbeddedResponse(
        id=profile.id,
        source_job_id=profile.source_job_id,
        provider_id=profile.provider_id,
        model_name=profile.model_name,
        source_filename=profile.source_filename,
        style_name=profile.style_name,
        analysis_report=analysis_report,
        style_summary=style_summary,
        prompt_pack=prompt_pack,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def build_job_detail_response(job: StyleAnalysisJob) -> StyleAnalysisJobResponse:
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
        style_profile_id=job.style_profile_id,
        analysis_meta=analysis_meta,
        analysis_report=analysis_report,
        style_summary=style_summary,
        prompt_pack=prompt_pack,
        style_profile=build_style_profile_embedded_response(job.style_profile),
    )


class StyleAnalysisJobService:
    def __init__(
        self,
        repository: StyleAnalysisJobRepository | None = None,
    ) -> None:
        self.repository = repository or StyleAnalysisJobRepository()
        self.provider_service = ProviderConfigService()

    async def list(
        self,
        session: AsyncSession,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> list[StyleAnalysisJob]:
        limit = min(max(limit, 1), 100)
        return await self.repository.list(
            session,
            offset=offset,
            limit=limit,
            include_payloads=False,
        )

    async def get_or_404(
        self, session: AsyncSession, job_id: str, *, include_payloads: bool = True
    ) -> StyleAnalysisJob:
        job = await self.repository.get_by_id(
            session,
            job_id,
            include_payloads=include_payloads,
        )
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分析任务不存在")
        return job

    async def get_detail_or_404(
        self,
        session: AsyncSession,
        job_id: str,
    ) -> StyleAnalysisJobResponse:
        job = await self.get_or_404(session, job_id, include_payloads=True)
        return build_job_detail_response(job)

    async def _get_payload_or_409(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        payload_column,
        parser,
        not_ready_detail: str,
    ):
        result = await self.repository.get_status_and_payload(
            session,
            job_id,
            payload_column=payload_column,
        )
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分析任务不存在")
        job_status, payload = result
        if job_status != STYLE_ANALYSIS_JOB_STATUS_SUCCEEDED or payload is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=not_ready_detail)
        return parser(payload)

    async def get_analysis_meta_or_409(
        self,
        session: AsyncSession,
        job_id: str,
    ) -> AnalysisMeta:
        return await self._get_payload_or_409(
            session,
            job_id,
            payload_column=StyleAnalysisJob.analysis_meta_payload,
            parser=AnalysisMeta.model_validate,
            not_ready_detail="分析任务尚未完成，暂无法读取元数据",
        )

    async def get_analysis_report_or_409(
        self,
        session: AsyncSession,
        job_id: str,
    ) -> AnalysisReport:
        return await self._get_payload_or_409(
            session,
            job_id,
            payload_column=StyleAnalysisJob.analysis_report_payload,
            parser=AnalysisReport.model_validate,
            not_ready_detail="分析任务尚未完成，暂无法读取分析报告",
        )

    async def get_style_summary_or_409(
        self,
        session: AsyncSession,
        job_id: str,
    ) -> StyleSummary:
        return await self._get_payload_or_409(
            session,
            job_id,
            payload_column=StyleAnalysisJob.style_summary_payload,
            parser=StyleSummary.model_validate,
            not_ready_detail="分析任务尚未完成，暂无法读取风格摘要",
        )

    async def get_prompt_pack_or_409(
        self,
        session: AsyncSession,
        job_id: str,
    ) -> PromptPack:
        return await self._get_payload_or_409(
            session,
            job_id,
            payload_column=StyleAnalysisJob.prompt_pack_payload,
            parser=PromptPack.model_validate,
            not_ready_detail="分析任务尚未完成，暂无法读取 Prompt 包",
        )

    async def claim_job_for_worker(
        self,
        session: AsyncSession,
        *,
        worker_id: str,
        max_attempts: int,
    ) -> str | None:
        return await self.repository.claim_pending_job(
            session,
            worker_id=worker_id,
            max_attempts=max_attempts,
            preparing_stage=STYLE_ANALYSIS_JOB_STAGE_PREPARING_INPUT,
            running_status=STYLE_ANALYSIS_JOB_STATUS_RUNNING,
            pending_status=STYLE_ANALYSIS_JOB_STATUS_PENDING,
            now=datetime.now(UTC),
        )

    async def heartbeat_job(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        stage: str | None,
    ) -> None:
        await self.repository.heartbeat(
            session,
            job_id,
            running_status=STYLE_ANALYSIS_JOB_STATUS_RUNNING,
            stage=stage,
            now=datetime.now(UTC),
        )

    async def mark_job_succeeded(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        result: StyleAnalysisPipelineResult,
    ) -> None:
        job = await self.get_or_404(session, job_id)
        job.analysis_meta_payload = result.analysis_meta.model_dump(mode="json")
        job.analysis_report_payload = result.analysis_report.model_dump(mode="json")
        job.style_summary_payload = result.style_summary.model_dump(mode="json")
        job.prompt_pack_payload = result.prompt_pack.model_dump(mode="json")
        job.status = STYLE_ANALYSIS_JOB_STATUS_SUCCEEDED
        job.stage = None
        job.error_message = None
        job.completed_at = datetime.now(UTC)
        job.locked_by = None
        job.locked_at = None
        job.last_heartbeat_at = None

    async def mark_job_failed(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        error_message: str,
    ) -> None:
        job = await self.get_or_404(session, job_id)
        job.status = STYLE_ANALYSIS_JOB_STATUS_FAILED
        job.stage = None
        job.error_message = error_message
        job.completed_at = datetime.now(UTC)
        job.locked_by = None
        job.locked_at = None
        job.last_heartbeat_at = None

    async def recover_stale_jobs(
        self,
        session: AsyncSession,
        *,
        stale_after_seconds: int,
        max_attempts: int,
    ) -> None:
        await self.repository.recover_stale_jobs(
            session,
            cutoff=datetime.now(UTC) - timedelta(seconds=stale_after_seconds),
            max_attempts=max_attempts,
            running_status=STYLE_ANALYSIS_JOB_STATUS_RUNNING,
            failed_status=STYLE_ANALYSIS_JOB_STATUS_FAILED,
            pending_status=STYLE_ANALYSIS_JOB_STATUS_PENDING,
            now=datetime.now(UTC),
        )

    async def create(
        self,
        session: AsyncSession,
        *,
        style_name: str,
        provider_id: str,
        model: str | None,
        upload_file: UploadFile,
    ) -> StyleAnalysisJob:
        provider = await self.provider_service.ensure_enabled(session, provider_id)
        file_name = (upload_file.filename or "").strip()

        sample_file = await self.repository.create_sample_file(
            session,
            original_filename=file_name,
            content_type=upload_file.content_type,
        )

        storage_service = StyleAnalysisStorageService()
        storage_path, total_bytes, checksum = await storage_service.save_file(
            sample_file.id,
            upload_file,
        )

        sample_file.storage_path = storage_path
        sample_file.byte_size = total_bytes
        sample_file.checksum_sha256 = checksum
        await self.repository.flush(session)

        selected_model = model.strip() if model else ""
        job = await self.repository.create_job(
            session,
            style_name=style_name.strip(),
            provider_id=provider.id,
            model_name=selected_model or provider.default_model,
            sample_file_id=sample_file.id,
            pending_status=STYLE_ANALYSIS_JOB_STATUS_PENDING,
        )

        return await self.get_or_404(session, job.id)
