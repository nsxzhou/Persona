from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.db.models import ProviderConfig, StyleAnalysisJob
from app.services.style_analysis_checkpointer import StyleAnalysisCheckpointerFactory
from app.services.style_analysis_jobs import StyleAnalysisJobService
from app.services.style_analysis_pipeline import (
    StyleAnalysisPipeline,
    StyleAnalysisPipelineResult,
)
from app.services.style_analysis_text import InputClassification, read_chunks_and_classification

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class StyleAnalysisRunContext:
    provider: ProviderConfig
    style_name: str
    model_name: str
    source_filename: str
    chunks: list[str]
    classification: InputClassification


class StyleAnalysisWorkerService:
    def __init__(self) -> None:
        self.job_service = StyleAnalysisJobService()
        self.checkpointer_factory = StyleAnalysisCheckpointerFactory()

    async def aclose(self) -> None:
        await self.checkpointer_factory.aclose()

    async def process_next_pending(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> bool:
        worker_id = f"style-worker-{uuid.uuid4()}"
        job_id = await self._claim_next_pending_job(session_factory, worker_id=worker_id)
        if job_id is None:
            return False

        await self._run_claimed_job(session_factory, job_id)
        return True

    async def _claim_next_pending_job(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        worker_id: str,
    ) -> str | None:
        settings = get_settings()
        async with session_factory() as session:
            candidate_id = await self.job_service.claim_job_for_worker(
                session,
                worker_id=worker_id,
                max_attempts=settings.style_analysis_max_attempts,
            )
            if candidate_id is None:
                await session.rollback()
                return None

            await session.commit()
            return candidate_id

    async def _run_claimed_job(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
    ) -> None:
        try:
            context = await self._load_run_context(session_factory, job_id)
            pipeline = await self._build_pipeline(
                provider=context.provider,
                model_name=context.model_name,
                style_name=context.style_name,
                source_filename=context.source_filename,
                stage_callback=lambda stage: self._touch_job_stage(
                    session_factory,
                    job_id,
                    stage=stage,
                ),
            )
            result = await pipeline.run(
                thread_id=job_id,
                chunks=context.chunks,
                classification=context.classification,
                max_concurrency=get_settings().style_analysis_chunk_max_concurrency,
            )
            await self._mark_job_succeeded(session_factory, job_id, result=result)
        except Exception as exc:
            logger.exception("style analysis job failed", extra={"job_id": job_id})
            await self._mark_job_failed(session_factory, job_id, error_message=str(exc))

    async def _load_run_context(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
    ) -> StyleAnalysisRunContext:
        async with session_factory() as session:
            job = await self.job_service.get_or_404(session, job_id)
            
            from app.services.style_analysis_storage import StyleAnalysisStorageService
            storage_service = StyleAnalysisStorageService()
            stream = storage_service.stream_file(job.sample_file.id)
            
            chunks, character_count, base_classification = await read_chunks_and_classification(
                stream,
                chunk_size=4000,
            )
            
            if not chunks:
                raise RuntimeError("切片后没有可分析的有效文本")

            classification: InputClassification = {
                **base_classification,
                "uses_batch_processing": len(chunks) > 1,
            }
            job.sample_file.character_count = character_count
            await session.commit()
            return StyleAnalysisRunContext(
                provider=job.provider,
                style_name=job.style_name,
                model_name=job.model_name,
                source_filename=job.sample_file.original_filename,
                chunks=chunks,
                classification=classification,
            )

    async def _build_pipeline(
        self,
        *,
        provider: ProviderConfig,
        model_name: str,
        style_name: str,
        source_filename: str,
        stage_callback,
    ) -> StyleAnalysisPipeline:
        return StyleAnalysisPipeline(
            provider=provider,
            model_name=model_name,
            style_name=style_name,
            source_filename=source_filename,
            checkpointer=await self.checkpointer_factory.get(),
            stage_callback=stage_callback,
        )

    async def _touch_job_stage(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
        *,
        stage: str | None,
    ) -> None:
        async with session_factory() as session:
            await session.execute(
                update(StyleAnalysisJob)
                .where(StyleAnalysisJob.id == job_id, StyleAnalysisJob.status == "running")
                .values(stage=stage, last_heartbeat_at=datetime.now(UTC))
            )
            await session.commit()

    async def _mark_job_succeeded(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
        *,
        result: StyleAnalysisPipelineResult,
    ) -> None:
        async with session_factory() as session:
            job = await self.job_service.get_or_404(session, job_id)
            job.analysis_meta_payload = result.analysis_meta.model_dump(mode="json")
            job.analysis_report_payload = result.analysis_report.model_dump(mode="json")
            job.style_summary_payload = result.style_summary.model_dump(mode="json")
            job.prompt_pack_payload = result.prompt_pack.model_dump(mode="json")
            job.status = "succeeded"
            job.stage = None
            job.error_message = None
            job.completed_at = datetime.now(UTC)
            job.locked_by = None
            job.locked_at = None
            job.last_heartbeat_at = None
            await session.commit()
            
        try:
            checkpointer = await self.checkpointer_factory.get()
            if hasattr(checkpointer, "adelete_thread"):
                await checkpointer.adelete_thread(job_id)
        except Exception:
            logger.exception("Failed to delete checkpointer thread", extra={"job_id": job_id})

    async def _mark_job_failed(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
        *,
        error_message: str,
    ) -> None:
        async with session_factory() as session:
            job = await self.job_service.get_or_404(session, job_id)
            job.status = "failed"
            job.stage = None
            job.error_message = error_message
            job.completed_at = datetime.now(UTC)
            job.locked_by = None
            job.locked_at = None
            job.last_heartbeat_at = None
            await session.commit()

        try:
            checkpointer = await self.checkpointer_factory.get()
            if hasattr(checkpointer, "adelete_thread"):
                await checkpointer.adelete_thread(job_id)
        except Exception:
            logger.exception("Failed to delete checkpointer thread", extra={"job_id": job_id})

    async def run_worker(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        poll_interval_seconds: float,
    ) -> None:
        while True:
            processed = await self.process_next_pending(session_factory)
            if not processed:
                await asyncio.sleep(poll_interval_seconds)

    async def fail_stale_running_jobs(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        stale_after_seconds: int,
    ) -> None:
        cutoff = datetime.now(UTC) - timedelta(seconds=stale_after_seconds)
        max_attempts = get_settings().style_analysis_max_attempts
        async with session_factory() as session:
            stale_condition = (StyleAnalysisJob.status == "running") & (
                func.coalesce(
                    StyleAnalysisJob.last_heartbeat_at,
                    StyleAnalysisJob.started_at,
                ) < cutoff
            )

            # 超过最大重试次数，标记为 failed
            await session.execute(
                update(StyleAnalysisJob)
                .where(stale_condition, StyleAnalysisJob.attempt_count >= max_attempts)
                .values(
                    status="failed",
                    error_message="分析任务重试次数已用尽，请重新提交",
                    completed_at=datetime.now(UTC),
                    stage=None,
                    locked_by=None,
                    locked_at=None,
                    last_heartbeat_at=None,
                )
            )

            # 未超过最大重试次数，重置为 pending
            await session.execute(
                update(StyleAnalysisJob)
                .where(stale_condition, StyleAnalysisJob.attempt_count < max_attempts)
                .values(
                    status="pending",
                    error_message=None,
                    completed_at=None,
                    stage=None,
                    locked_by=None,
                    locked_at=None,
                    last_heartbeat_at=None,
                )
            )

            await session.commit()
