from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain_errors import ConflictError, NotFoundError
from app.db.models import StyleAnalysisJob, StyleProfile
from app.db.repositories.style_analysis_jobs import StyleAnalysisJobRepository
from app.schemas.style_analysis_jobs import (
    AnalysisMeta,
    STYLE_ANALYSIS_JOB_STAGE_PREPARING_INPUT,
    STYLE_ANALYSIS_JOB_STATUS_FAILED,
    STYLE_ANALYSIS_JOB_STATUS_PENDING,
    STYLE_ANALYSIS_JOB_STATUS_RUNNING,
    STYLE_ANALYSIS_JOB_STATUS_SUCCEEDED,
    StyleAnalysisJobResponse,
    StyleAnalysisJobStatusResponse,
    StyleProfileEmbeddedResponse,
)
from app.services.provider_configs import ProviderConfigService
from app.services.style_lab_mappers import (
    build_job_result_bundle,
    build_profile_result_bundle,
    build_style_profile_response_payload,
)
from app.services.style_analysis_pipeline import StyleAnalysisPipelineResult
from app.services.style_analysis_job_file_lifecycle import (
    StyleAnalysisJobFileLifecycleService,
)

STYLE_ANALYSIS_USER_ERROR_MESSAGE = "分析任务失败，请稍后重试。"


def sanitize_style_analysis_error_message(error_message: str | None) -> str:
    if error_message is None:
        return STYLE_ANALYSIS_USER_ERROR_MESSAGE
    normalized_message = error_message.strip()
    if not normalized_message:
        return STYLE_ANALYSIS_USER_ERROR_MESSAGE
    return normalized_message


def build_style_profile_embedded_response(
    profile: StyleProfile | None,
) -> StyleProfileEmbeddedResponse | None:
    if profile is None:
        return None
    return StyleProfileEmbeddedResponse(**build_style_profile_response_payload(profile))


def build_job_detail_response(job: StyleAnalysisJob) -> StyleAnalysisJobResponse:
    style_profile = build_style_profile_embedded_response(job.style_profile)
    analysis_meta, analysis_report_markdown, style_summary_markdown, prompt_pack_markdown = (
        build_job_result_bundle(job)
    )
    if style_profile is not None:
        analysis_report_markdown = style_profile.analysis_report_markdown
        style_summary_markdown = style_profile.style_summary_markdown
        prompt_pack_markdown = style_profile.prompt_pack_markdown
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
        analysis_report_markdown=analysis_report_markdown,
        style_summary_markdown=style_summary_markdown,
        prompt_pack_markdown=prompt_pack_markdown,
        style_profile=style_profile,
    )


class StyleAnalysisJobService:
    def __init__(
        self,
        repository: StyleAnalysisJobRepository | None = None,
    ) -> None:
        self.repository = repository or StyleAnalysisJobRepository()
        self.provider_service = ProviderConfigService()
        self.file_lifecycle = StyleAnalysisJobFileLifecycleService()

    async def list(
        self,
        session: AsyncSession,
        *,
        user_id: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[StyleAnalysisJob]:
        limit = min(max(limit, 1), 100)
        return await self.repository.list(
            session,
            user_id=user_id,
            offset=offset,
            limit=limit,
            include_payloads=False,
        )

    async def get_or_404(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str | None = None,
        include_payloads: bool = True,
    ) -> StyleAnalysisJob:
        job = await self.repository.get_by_id(
            session,
            job_id,
            user_id=user_id,
            include_payloads=include_payloads,
        )
        if job is None:
            raise NotFoundError("分析任务不存在")
        return job

    async def get_detail_or_404(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str | None = None,
    ) -> StyleAnalysisJobResponse:
        if user_id is None:
            job = await self.repository.get_by_id(
                session,
                job_id,
                include_payloads=True,
                include_style_profile_payloads=True,
            )
        else:
            job = await self.repository.get_by_id(
                session,
                job_id,
                user_id=user_id,
                include_payloads=True,
                include_style_profile_payloads=True,
            )
        if job is None:
            raise NotFoundError("分析任务不存在")
        return build_job_detail_response(job)

    async def get_status_or_404(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str | None = None,
    ) -> StyleAnalysisJobStatusResponse:
        job = await self.get_or_404(
            session,
            job_id,
            user_id=user_id,
            include_payloads=False,
        )
        return StyleAnalysisJobStatusResponse(
            id=job.id,
            status=job.status,
            stage=job.stage,
            error_message=job.error_message,
            updated_at=job.updated_at,
        )

    async def _get_payload_or_409(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str | None = None,
        payload_column,
        parser,
        not_ready_detail: str,
    ):
        if user_id is None:
            result = await self.repository.get_status_and_payload(
                session,
                job_id,
                payload_column=payload_column,
            )
        else:
            result = await self.repository.get_status_and_payload(
                session,
                job_id,
                user_id=user_id,
                payload_column=payload_column,
            )
        if result is None:
            raise NotFoundError("分析任务不存在")
        job_status, payload = result
        if job_status != STYLE_ANALYSIS_JOB_STATUS_SUCCEEDED or payload is None:
            raise ConflictError(not_ready_detail)
        return parser(payload)

    async def get_analysis_meta_or_409(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str | None = None,
    ) -> AnalysisMeta:
        return await self._get_payload_or_409(
            session,
            job_id,
            user_id=user_id,
            payload_column=StyleAnalysisJob.analysis_meta_payload,
            parser=AnalysisMeta.model_validate,
            not_ready_detail="分析任务尚未完成，暂无法读取元数据",
        )

    async def get_analysis_report_or_409(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str | None = None,
    ) -> str:
        return await self._get_payload_or_409(
            session,
            job_id,
            user_id=user_id,
            payload_column=StyleAnalysisJob.analysis_report_payload,
            parser=str,
            not_ready_detail="分析任务尚未完成，暂无法读取分析报告",
        )

    async def get_style_summary_or_409(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str | None = None,
    ) -> str:
        return await self._get_payload_or_409(
            session,
            job_id,
            user_id=user_id,
            payload_column=StyleAnalysisJob.style_summary_payload,
            parser=str,
            not_ready_detail="分析任务尚未完成，暂无法读取风格摘要",
        )

    async def get_prompt_pack_or_409(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str | None = None,
    ) -> str:
        return await self._get_payload_or_409(
            session,
            job_id,
            user_id=user_id,
            payload_column=StyleAnalysisJob.prompt_pack_payload,
            parser=str,
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
        job.analysis_report_payload = result.analysis_report_markdown
        job.style_summary_payload = result.style_summary_markdown
        job.prompt_pack_payload = result.prompt_pack_markdown
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
        max_attempts: int,
    ) -> bool:
        job = await self.get_or_404(session, job_id)
        retryable = job.attempt_count < max_attempts
        job.status = (
            STYLE_ANALYSIS_JOB_STATUS_PENDING
            if retryable
            else STYLE_ANALYSIS_JOB_STATUS_FAILED
        )
        job.stage = None
        job.error_message = (
            None if retryable else sanitize_style_analysis_error_message(error_message)
        )
        job.started_at = None if retryable else job.started_at
        job.completed_at = None if retryable else datetime.now(UTC)
        job.locked_by = None
        job.locked_at = None
        job.last_heartbeat_at = None
        return not retryable

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
        user_id: str | None = None,
        style_name: str,
        provider_id: str,
        model: str | None,
        upload_file: UploadFile,
    ) -> StyleAnalysisJob:
        provider = await self.provider_service.ensure_enabled(
            session,
            provider_id,
            user_id=user_id,
        )
        resolved_user_id = user_id or provider.user_id
        file_name = (upload_file.filename or "").strip()

        sample_file = await self.repository.create_sample_file(
            session,
            user_id=resolved_user_id,
            original_filename=file_name,
            content_type=upload_file.content_type,
        )

        storage_path, total_bytes, checksum = await self.file_lifecycle.persist_sample_upload(
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
            user_id=resolved_user_id,
            style_name=style_name.strip(),
            provider_id=provider.id,
            model_name=selected_model or provider.default_model,
            sample_file_id=sample_file.id,
            pending_status=STYLE_ANALYSIS_JOB_STATUS_PENDING,
        )

        return await self.get_or_404(
            session,
            job.id,
            user_id=resolved_user_id,
            include_payloads=False,
        )

    async def delete(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str | None = None,
    ) -> None:
        job = await self.repository.get_for_delete(session, job_id, user_id=user_id)
        if job is None:
            raise NotFoundError("分析任务不存在")
        if job.style_profile is not None and job.style_profile.projects:
            raise ConflictError("该分析任务的风格档案正被项目引用，无法删除")

        sample_storage_path = job.sample_file.storage_path
        await self.repository.delete_job_graph(session, job)
        await self.file_lifecycle.cleanup_after_job_delete(
            sample_storage_path=sample_storage_path,
            job_id=job_id,
        )
