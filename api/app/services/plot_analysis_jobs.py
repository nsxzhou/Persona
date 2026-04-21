from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain_errors import ConflictError, NotFoundError
from app.db.models import PlotAnalysisJob
from app.db.repositories.plot_analysis_jobs import PlotAnalysisJobRepository
from app.schemas.plot_analysis_jobs import (
    PLOT_ANALYSIS_JOB_STAGE_PREPARING_INPUT,
    PLOT_ANALYSIS_JOB_STATUS_FAILED,
    PLOT_ANALYSIS_JOB_STATUS_PAUSED,
    PLOT_ANALYSIS_JOB_STATUS_PENDING,
    PLOT_ANALYSIS_JOB_STATUS_RUNNING,
    PLOT_ANALYSIS_JOB_STATUS_SUCCEEDED,
    PlotAnalysisJobLogsResponse,
    PlotAnalysisJobStatusResponse,
    PlotAnalysisMeta,
)
from app.services.plot_analysis_checkpointer import PlotAnalysisCheckpointerFactory
from app.services.plot_analysis_storage import PlotAnalysisStorageService
from app.services.provider_configs import ProviderConfigService

PLOT_ANALYSIS_USER_ERROR_MESSAGE = "分析任务失败，请稍后重试。"
logger = logging.getLogger(__name__)


def sanitize_plot_analysis_error_message(error_message: str | None) -> str:
    if error_message is None:
        return PLOT_ANALYSIS_USER_ERROR_MESSAGE
    normalized_message = error_message.strip()
    if not normalized_message:
        return PLOT_ANALYSIS_USER_ERROR_MESSAGE
    return normalized_message


def _reset_job_to_pending(
    job: PlotAnalysisJob,
    *,
    target_status: str = PLOT_ANALYSIS_JOB_STATUS_PENDING,
    reset_attempts: bool = False,
    paused_at: datetime | None = None,
) -> None:
    job.status = target_status
    job.stage = None
    job.error_message = None
    job.started_at = None
    job.completed_at = None
    job.locked_by = None
    job.locked_at = None
    job.last_heartbeat_at = None
    job.pause_requested_at = None
    job.paused_at = paused_at
    if reset_attempts:
        job.attempt_count = 0


class PlotAnalysisJobService:
    def __init__(
        self,
        repository: PlotAnalysisJobRepository | None = None,
    ) -> None:
        self.repository = repository or PlotAnalysisJobRepository()
        self.provider_service = ProviderConfigService()
        self.storage_service = PlotAnalysisStorageService()
        self.checkpointer_factory = PlotAnalysisCheckpointerFactory()

    async def list(
        self,
        session: AsyncSession,
        *,
        user_id: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[PlotAnalysisJob]:
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
    ) -> PlotAnalysisJob:
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
    ) -> PlotAnalysisJob:
        if user_id is None:
            job = await self.repository.get_by_id(
                session,
                job_id,
                include_payloads=True,
                include_plot_profile_payloads=True,
            )
        else:
            job = await self.repository.get_by_id(
                session,
                job_id,
                user_id=user_id,
                include_payloads=True,
                include_plot_profile_payloads=True,
            )
        if job is None:
            raise NotFoundError("分析任务不存在")
        return job

    async def get_status_or_404(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str | None = None,
    ) -> PlotAnalysisJobStatusResponse:
        job = await self.get_or_404(
            session,
            job_id,
            user_id=user_id,
            include_payloads=False,
        )
        return PlotAnalysisJobStatusResponse(
            id=job.id,
            status=job.status,
            stage=job.stage,
            error_message=job.error_message,
            updated_at=job.updated_at,
            pause_requested_at=job.pause_requested_at,
        )

    async def get_job_logs_or_404(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str | None = None,
        offset: int = 0,
    ) -> PlotAnalysisJobLogsResponse:
        await self.get_or_404(
            session,
            job_id,
            user_id=user_id,
            include_payloads=False,
        )
        content, next_offset, truncated = await self.storage_service.read_job_logs_incremental(
            job_id,
            offset=offset,
        )
        return PlotAnalysisJobLogsResponse(
            content=content,
            next_offset=next_offset,
            truncated=truncated,
        )

    async def resume(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str | None = None,
    ) -> PlotAnalysisJobStatusResponse:
        job = await self.get_or_404(
            session,
            job_id,
            user_id=user_id,
            include_payloads=False,
        )
        if job.status == PLOT_ANALYSIS_JOB_STATUS_RUNNING and job.locked_by:
            raise ConflictError("分析任务正在运行，无法恢复")
        if job.status == PLOT_ANALYSIS_JOB_STATUS_SUCCEEDED:
            raise ConflictError("分析任务已成功完成，无需恢复")
        if job.status == PLOT_ANALYSIS_JOB_STATUS_PAUSED:
            _reset_job_to_pending(job)
            await session.flush()
            return await self.get_status_or_404(session, job_id, user_id=user_id)
        _reset_job_to_pending(job, reset_attempts=True)
        await session.flush()
        return await self.get_status_or_404(session, job_id, user_id=user_id)

    async def pause(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str | None = None,
    ) -> PlotAnalysisJobStatusResponse:
        job = await self.get_or_404(
            session,
            job_id,
            user_id=user_id,
            include_payloads=False,
        )
        if job.status == PLOT_ANALYSIS_JOB_STATUS_SUCCEEDED:
            raise ConflictError("分析任务已成功完成，无法暂停")
        if job.status == PLOT_ANALYSIS_JOB_STATUS_FAILED:
            raise ConflictError("分析任务已失败，无法暂停")
        if job.status == PLOT_ANALYSIS_JOB_STATUS_PAUSED:
            return await self.get_status_or_404(session, job_id, user_id=user_id)
        if job.status == PLOT_ANALYSIS_JOB_STATUS_PENDING:
            _reset_job_to_pending(
                job,
                target_status=PLOT_ANALYSIS_JOB_STATUS_PAUSED,
                paused_at=datetime.now(UTC),
            )
            await session.flush()
            return await self.get_status_or_404(session, job_id, user_id=user_id)
        await self.repository.request_pause(
            session,
            job_id,
            running_status=PLOT_ANALYSIS_JOB_STATUS_RUNNING,
            now=datetime.now(UTC),
        )
        await session.flush()
        return await self.get_status_or_404(session, job_id, user_id=user_id)

    async def _get_payload_or_409(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str | None = None,
        payload_column=None,
        parser=None,
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
        if job_status != PLOT_ANALYSIS_JOB_STATUS_SUCCEEDED or payload is None:
            raise ConflictError(not_ready_detail)
        return parser(payload)

    async def get_analysis_meta_or_409(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str | None = None,
    ) -> PlotAnalysisMeta:
        return await self._get_payload_or_409(
            session,
            job_id,
            user_id=user_id,
            payload_column=PlotAnalysisJob.analysis_meta_payload,
            parser=PlotAnalysisMeta.model_validate,
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
            payload_column=PlotAnalysisJob.analysis_report_payload,
            parser=str,
            not_ready_detail="分析任务尚未完成，暂无法读取分析报告",
        )

    async def get_plot_summary_or_409(
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
            payload_column=PlotAnalysisJob.plot_summary_payload,
            parser=str,
            not_ready_detail="分析任务尚未完成，暂无法读取情节摘要",
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
            payload_column=PlotAnalysisJob.prompt_pack_payload,
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
            preparing_stage=PLOT_ANALYSIS_JOB_STAGE_PREPARING_INPUT,
            running_status=PLOT_ANALYSIS_JOB_STATUS_RUNNING,
            pending_status=PLOT_ANALYSIS_JOB_STATUS_PENDING,
            now=datetime.now(UTC),
        )

    async def heartbeat_job(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        stage: str | None,
    ) -> datetime | None:
        return await self.repository.heartbeat(
            session,
            job_id,
            running_status=PLOT_ANALYSIS_JOB_STATUS_RUNNING,
            stage=stage,
            now=datetime.now(UTC),
        )

    async def mark_job_paused(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        stage: str | None,
    ) -> None:
        await self.repository.mark_paused(
            session,
            job_id,
            paused_status=PLOT_ANALYSIS_JOB_STATUS_PAUSED,
            now=datetime.now(UTC),
            stage=stage,
        )

    async def mark_job_succeeded(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        analysis_meta_payload: dict,
        analysis_report_payload: str,
        plot_summary_payload: str,
        prompt_pack_payload: str,
    ) -> None:
        job = await self.get_or_404(session, job_id)
        job.analysis_meta_payload = analysis_meta_payload
        job.analysis_report_payload = analysis_report_payload
        job.plot_summary_payload = plot_summary_payload
        job.prompt_pack_payload = prompt_pack_payload
        job.status = PLOT_ANALYSIS_JOB_STATUS_SUCCEEDED
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
            PLOT_ANALYSIS_JOB_STATUS_PENDING
            if retryable
            else PLOT_ANALYSIS_JOB_STATUS_FAILED
        )
        job.stage = None
        job.error_message = (
            None if retryable else sanitize_plot_analysis_error_message(error_message)
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
            running_status=PLOT_ANALYSIS_JOB_STATUS_RUNNING,
            paused_status=PLOT_ANALYSIS_JOB_STATUS_PAUSED,
            failed_status=PLOT_ANALYSIS_JOB_STATUS_FAILED,
            pending_status=PLOT_ANALYSIS_JOB_STATUS_PENDING,
            now=datetime.now(UTC),
        )

    async def create(
        self,
        session: AsyncSession,
        *,
        user_id: str | None = None,
        plot_name: str,
        provider_id: str,
        model: str | None,
        original_filename: str,
        content_type: str | None,
        content_stream: AsyncIterator[bytes],
    ) -> PlotAnalysisJob:
        provider = await self.provider_service.ensure_enabled(
            session,
            provider_id,
            user_id=user_id,
        )
        resolved_user_id = user_id or provider.user_id
        file_name = original_filename.strip()

        sample_file = await self.repository.create_sample_file(
            session,
            user_id=resolved_user_id,
            original_filename=file_name,
            content_type=content_type,
        )
        storage_path, total_bytes, checksum = await self.storage_service.save_file(
            sample_file.id,
            content_stream,
        )

        sample_file.storage_path = storage_path
        sample_file.byte_size = total_bytes
        sample_file.checksum_sha256 = checksum
        await self.repository.flush(session)

        selected_model = model.strip() if model else ""
        job = await self.repository.create_job(
            session,
            user_id=resolved_user_id,
            plot_name=plot_name.strip(),
            provider_id=provider.id,
            model_name=selected_model or provider.default_model,
            sample_file_id=sample_file.id,
            pending_status=PLOT_ANALYSIS_JOB_STATUS_PENDING,
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
        if sample_storage_path:
            try:
                Path(sample_storage_path).unlink(missing_ok=True)
            except OSError:
                logger.exception("Failed to delete plot sample file", extra={"job_id": job_id})

        try:
            await self.storage_service.cleanup_job_artifacts(job_id)
        except OSError:
            logger.exception("Failed to cleanup plot analysis artifacts", extra={"job_id": job_id})

        try:
            await self.checkpointer_factory.delete_thread(job_id)
        except Exception:
            logger.exception("Failed to cleanup plot analysis checkpoint", extra={"job_id": job_id})

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
        if job.plot_profile is not None and job.plot_profile.projects:
            raise ConflictError("该分析任务的情节档案正被项目引用，无法删除")

        sample_storage_path = job.sample_file.storage_path
        await self.repository.delete_job_graph(session, job)
        await session.flush()
        await self._delete_job_external_resources(
            job_id=job_id,
            sample_storage_path=sample_storage_path,
        )
