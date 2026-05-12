from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
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
from app.services.analysis_jobs import (
    cleanup_analysis_job_external_resources,
    mark_analysis_job_failed,
    reconcile_stale_running_job,
    reconcile_unacknowledged_pause_request,
    reset_analysis_job_to_pending,
    sanitize_analysis_error_message,
    resolve_analysis_payload_result_or_409,
)
from app.services.analysis_uploads import clean_txt_upload_stream, ensure_txt_upload_filename
from app.services.checkpointer_factory import PlotAnalysisCheckpointerFactory
from app.services.plot_analysis_storage import PlotAnalysisStorageService
from app.services.provider_configs import ProviderConfigService

PLOT_ANALYSIS_USER_ERROR_MESSAGE = "分析任务失败，请稍后重试。"
logger = logging.getLogger(__name__)


def sanitize_plot_analysis_error_message(error_message: str | None) -> str:
    return sanitize_analysis_error_message(
        error_message,
        fallback=PLOT_ANALYSIS_USER_ERROR_MESSAGE,
    )


def _reset_job_to_pending(
    job: PlotAnalysisJob,
    *,
    target_status: str = PLOT_ANALYSIS_JOB_STATUS_PENDING,
    reset_attempts: bool = False,
    paused_at: datetime | None = None,
) -> None:
    reset_analysis_job_to_pending(
        job,
        target_status=target_status,
        reset_attempts=reset_attempts,
        paused_at=paused_at,
    )


class PlotAnalysisJobService:
    def __init__(
        self,
        repository: PlotAnalysisJobRepository | None = None,
        provider_service: ProviderConfigService | None = None,
        storage_service: PlotAnalysisStorageService | None = None,
        checkpointer_factory: PlotAnalysisCheckpointerFactory | None = None,
    ) -> None:
        self.repository = repository or PlotAnalysisJobRepository()
        self.provider_service = provider_service or ProviderConfigService()
        self.storage_service = storage_service or PlotAnalysisStorageService()
        self.checkpointer_factory = checkpointer_factory or PlotAnalysisCheckpointerFactory()

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
            raise NotFoundError(f"分析任务不存在: job_id={job_id}")
        return job

    async def get_detail_or_404(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str | None = None,
    ) -> PlotAnalysisJob:
        job = await self.repository.get_by_id(
            session,
            job_id,
            user_id=user_id,
            include_payloads=True,
            include_plot_profile_payloads=True,
        )
        if job is None:
            raise NotFoundError(f"分析任务不存在: job_id={job_id}")
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
        if await self._reconcile_pause_request_if_unacknowledged(session, job):
            job = await self.get_or_404(
                session,
                job_id,
                user_id=user_id,
                include_payloads=False,
            )
        if await self._reconcile_stale_job_if_needed(session, job):
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
        refreshed = await self.get_or_404(
            session,
            job_id,
            user_id=user_id,
            include_payloads=False,
        )
        await self._reconcile_pause_request_if_unacknowledged(session, refreshed)
        await self._reconcile_stale_job_if_needed(session, refreshed)
        return await self.get_status_or_404(session, job_id, user_id=user_id)

    async def _reconcile_pause_request_if_unacknowledged(
        self,
        session: AsyncSession,
        job: PlotAnalysisJob,
    ) -> bool:
        settings = get_settings()
        return await reconcile_unacknowledged_pause_request(
            session,
            job,
            repository=self.repository,
            running_status=PLOT_ANALYSIS_JOB_STATUS_RUNNING,
            paused_status=PLOT_ANALYSIS_JOB_STATUS_PAUSED,
            pause_confirm_timeout_seconds=settings.analysis_pause_confirm_timeout_seconds,
        )

    async def _reconcile_stale_job_if_needed(
        self,
        session: AsyncSession,
        job: PlotAnalysisJob,
    ) -> bool:
        settings = get_settings()
        return await reconcile_stale_running_job(
            session,
            job,
            repository=self.repository,
            stale_timeout_seconds=settings.style_analysis_stale_timeout_seconds,
            max_attempts=settings.plot_analysis_max_attempts,
            running_status=PLOT_ANALYSIS_JOB_STATUS_RUNNING,
            paused_status=PLOT_ANALYSIS_JOB_STATUS_PAUSED,
            failed_status=PLOT_ANALYSIS_JOB_STATUS_FAILED,
            pending_status=PLOT_ANALYSIS_JOB_STATUS_PENDING,
        )

    async def _resolve_payload_result_or_409(
        self,
        *,
        job_id: str,
        result,
        parser,
        not_ready_detail: str,
    ):
        return resolve_analysis_payload_result_or_409(
            result,
            job_id=job_id,
            succeeded_status=PLOT_ANALYSIS_JOB_STATUS_SUCCEEDED,
            parser=parser,
            not_ready_detail=not_ready_detail,
        )

    async def get_analysis_meta_or_409(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str | None = None,
    ) -> PlotAnalysisMeta:
        result = await self.repository.get_status_and_analysis_meta(
            session,
            job_id,
            user_id=user_id,
        )
        return await self._resolve_payload_result_or_409(
            job_id=job_id,
            result=result,
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
        result = await self.repository.get_status_and_analysis_report(
            session,
            job_id,
            user_id=user_id,
        )
        return await self._resolve_payload_result_or_409(
            job_id=job_id,
            result=result,
            parser=str,
            not_ready_detail="分析任务尚未完成，暂无法读取分析报告",
        )

    async def get_plot_skeleton_or_409(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str | None = None,
    ) -> str:
        result = await self.repository.get_status_and_plot_skeleton(
            session,
            job_id,
            user_id=user_id,
        )
        return await self._resolve_payload_result_or_409(
            job_id=job_id,
            result=result,
            parser=str,
            not_ready_detail="分析任务尚未完成，暂无法读取全书骨架",
        )

    async def get_story_engine_or_409(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str | None = None,
    ) -> str:
        result = await self.repository.get_status_and_story_engine(
            session,
            job_id,
            user_id=user_id,
        )
        return await self._resolve_payload_result_or_409(
            job_id=job_id,
            result=result,
            parser=str,
            not_ready_detail="分析任务尚未完成，暂无法读取 Plot Writing Guide",
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
        story_engine_payload: str,
        plot_skeleton_payload: str,
    ) -> None:
        job = await self.get_or_404(session, job_id)
        job.analysis_meta_payload = analysis_meta_payload
        job.analysis_report_payload = analysis_report_payload
        job.story_engine_payload = story_engine_payload
        job.plot_skeleton_payload = plot_skeleton_payload
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
        return mark_analysis_job_failed(
            job,
            pending_status=PLOT_ANALYSIS_JOB_STATUS_PENDING,
            failed_status=PLOT_ANALYSIS_JOB_STATUS_FAILED,
            error_message=error_message,
            max_attempts=max_attempts,
            sanitize_error_message=sanitize_plot_analysis_error_message,
        )

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
        upload_file,
    ) -> PlotAnalysisJob:
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
        await cleanup_analysis_job_external_resources(
            job_id=job_id,
            sample_storage_path=sample_storage_path,
            storage_service=self.storage_service,
            checkpointer_factory=self.checkpointer_factory,
            logger=logger,
            sample_delete_error_message="Failed to delete plot sample file",
            artifact_cleanup_error_message="Failed to cleanup plot analysis artifacts",
            checkpoint_cleanup_error_message="Failed to cleanup plot analysis checkpoint",
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
        if job.plot_profile is not None and job.plot_profile.projects:
            raise ConflictError("该分析任务的情节档案正被项目引用，无法删除")

        sample_storage_path = job.sample_file.storage_path
        await self.repository.delete_job_graph(session, job)
        await session.flush()
        await self._delete_job_external_resources(
            job_id=job_id,
            sample_storage_path=sample_storage_path,
        )
