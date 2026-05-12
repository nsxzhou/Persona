from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.domain_errors import ConflictError, NotFoundError
from app.db.models import StyleAnalysisJob
from app.db.repositories.style_analysis_jobs import StyleAnalysisJobRepository
from app.schemas.style_analysis_jobs import (
    AnalysisMeta,
    STYLE_ANALYSIS_JOB_STAGE_PREPARING_INPUT,
    STYLE_ANALYSIS_JOB_STATUS_FAILED,
    STYLE_ANALYSIS_JOB_STATUS_PENDING,
    STYLE_ANALYSIS_JOB_STATUS_PAUSED,
    STYLE_ANALYSIS_JOB_STATUS_RUNNING,
    STYLE_ANALYSIS_JOB_STATUS_SUCCEEDED,
    StyleAnalysisJobLogsResponse,
    StyleAnalysisJobStatusResponse,
)
from app.services.analysis_jobs import (
    BaseAnalysisJobService,
    cleanup_analysis_job_external_resources,
    resolve_analysis_payload_result_or_409,
    sanitize_analysis_error_message,
)
from app.services.analysis_uploads import clean_txt_upload_stream, ensure_txt_upload_filename
from app.services.provider_configs import ProviderConfigService
from app.services.style_analysis_storage import StyleAnalysisStorageService
from app.services.style_analysis_checkpointer import StyleAnalysisCheckpointerFactory

STYLE_ANALYSIS_USER_ERROR_MESSAGE = "分析任务失败，请稍后重试。"
logger = logging.getLogger(__name__)


def sanitize_style_analysis_error_message(error_message: str | None) -> str:
    return sanitize_analysis_error_message(
        error_message,
        fallback=STYLE_ANALYSIS_USER_ERROR_MESSAGE,
    )


class StyleAnalysisJobService(BaseAnalysisJobService):
    job_not_found_message = "分析任务不存在: job_id={job_id}"
    status_response_type = StyleAnalysisJobStatusResponse
    job_logs_response_type = StyleAnalysisJobLogsResponse
    preparing_stage = STYLE_ANALYSIS_JOB_STAGE_PREPARING_INPUT
    pending_status = STYLE_ANALYSIS_JOB_STATUS_PENDING
    running_status = STYLE_ANALYSIS_JOB_STATUS_RUNNING
    paused_status = STYLE_ANALYSIS_JOB_STATUS_PAUSED
    failed_status = STYLE_ANALYSIS_JOB_STATUS_FAILED
    succeeded_status = STYLE_ANALYSIS_JOB_STATUS_SUCCEEDED
    stale_timeout_setting_name = "style_analysis_stale_timeout_seconds"
    max_attempts_setting_name = "style_analysis_max_attempts"
    sanitize_error_message = staticmethod(sanitize_style_analysis_error_message)

    def __init__(
        self,
        repository: StyleAnalysisJobRepository | None = None,
        provider_service: ProviderConfigService | None = None,
        storage_service: StyleAnalysisStorageService | None = None,
        checkpointer_factory: StyleAnalysisCheckpointerFactory | None = None,
    ) -> None:
        self.repository = repository or StyleAnalysisJobRepository()
        self.provider_service = provider_service or ProviderConfigService()
        self.storage_service = storage_service or StyleAnalysisStorageService()
        self.checkpointer_factory = checkpointer_factory or StyleAnalysisCheckpointerFactory()

    async def get_detail_or_404(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str | None = None,
    ) -> StyleAnalysisJob:
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
            raise NotFoundError(f"分析任务不存在: job_id={job_id}")
        return job

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
        return resolve_analysis_payload_result_or_409(
            result,
            job_id=job_id,
            succeeded_status=STYLE_ANALYSIS_JOB_STATUS_SUCCEEDED,
            parser=parser,
            not_ready_detail=not_ready_detail,
        )

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

    async def get_voice_profile_or_409(
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
            payload_column=StyleAnalysisJob.voice_profile_payload,
            parser=str,
            not_ready_detail="分析任务尚未完成，暂无法读取 Voice Profile",
        )

    async def mark_job_succeeded(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        analysis_meta_payload: dict,
        analysis_report_payload: str,
        voice_profile_payload: str,
    ) -> None:
        job = await self.get_or_404(session, job_id)
        job.analysis_meta_payload = analysis_meta_payload
        job.analysis_report_payload = analysis_report_payload
        job.voice_profile_payload = voice_profile_payload
        job.status = STYLE_ANALYSIS_JOB_STATUS_SUCCEEDED
        job.stage = None
        job.error_message = None
        job.completed_at = datetime.now(UTC)
        job.locked_by = None
        job.locked_at = None
        job.last_heartbeat_at = None

    async def create(
        self,
        session: AsyncSession,
        *,
        user_id: str | None = None,
        style_name: str,
        provider_id: str,
        model: str | None,
        upload_file,
    ) -> StyleAnalysisJob:
        provider = await self.provider_service.ensure_enabled(
            session,
            provider_id,
            user_id=user_id,
        )
        resolved_user_id = user_id or provider.user_id
        file_name = ensure_txt_upload_filename(upload_file.filename)
        settings = get_settings()
        max_bytes = getattr(settings, "style_analysis_max_upload_bytes", 0) or 0

        sample_file = await self.repository.create_sample_file(
            session,
            user_id=resolved_user_id,
            original_filename=file_name,
            content_type=upload_file.content_type,
        )
        storage_path, total_bytes, checksum = await self.storage_service.save_file(
            sample_file.id,
            clean_txt_upload_stream(upload_file, max_bytes=max_bytes),
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

    async def _delete_job_external_resources(
        self,
        *,
        job_id: str,
        sample_storage_path: str | None,
    ) -> None:
        await cleanup_analysis_job_external_resources(
            job_id=job_id,
            sample_storage_path=sample_storage_path,
            storage_service=self.storage_service,
            checkpointer_factory=self.checkpointer_factory,
            logger=logger,
            sample_delete_error_message="Failed to delete sample file",
            artifact_cleanup_error_message="Failed to cleanup style analysis artifacts",
            checkpoint_cleanup_error_message="Failed to cleanup style analysis checkpoint",
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
            raise NotFoundError(f"分析任务不存在: job_id={job_id}")
        if job.style_profile is not None and job.style_profile.projects:
            raise ConflictError("该分析任务的风格档案正被项目引用，无法删除")

        sample_storage_path = job.sample_file.storage_path
        await self.repository.delete_job_graph(session, job)
        await session.flush()
        await self._delete_job_external_resources(
            job_id=job_id,
            sample_storage_path=sample_storage_path,
        )
