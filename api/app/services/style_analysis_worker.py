from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.db.models import ProviderConfig
from app.services.style_analysis_checkpointer import StyleAnalysisCheckpointerFactory
from app.services.style_analysis_jobs import StyleAnalysisJobService
from app.services.style_analysis_pipeline import (
    StyleAnalysisPipeline,
    StyleAnalysisPipelineResult,
)
from app.services.style_analysis_storage import StyleAnalysisStorageService
from app.services.style_analysis_text import InputClassification, read_chunks_and_classification

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StyleAnalysisRunContext:
    provider: ProviderConfig
    style_name: str
    model_name: str
    source_filename: str
    chunk_count: int
    classification: InputClassification


class StyleAnalysisWorkerService:
    def __init__(self) -> None:
        self.job_service = StyleAnalysisJobService()
        self.checkpointer_factory = StyleAnalysisCheckpointerFactory()
        self.storage_service = StyleAnalysisStorageService()

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
                job_id=job_id,
                chunk_count=context.chunk_count,
                classification=context.classification,
                max_concurrency=get_settings().style_analysis_chunk_max_concurrency,
            )
            await self._mark_job_succeeded(session_factory, job_id, result=result)
        except Exception as exc:
            logger.exception("style analysis job failed", extra={"job_id": job_id})
            await self._mark_job_failed(session_factory, job_id, error_message=str(exc))
        finally:
            await self.storage_service.cleanup_job_artifacts(job_id)
            await self._delete_checkpointer_thread(job_id)

    async def _load_run_context(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
    ) -> StyleAnalysisRunContext:
        async with session_factory() as session:
            job = await self.job_service.get_or_404(session, job_id)
            chunks, character_count, base_classification = await read_chunks_and_classification(
                self.storage_service.stream_file(job.sample_file.id),
                chunk_size=4000,
            )

            if not chunks:
                raise RuntimeError("切片后没有可分析的有效文本")

            for index, chunk in enumerate(chunks):
                await self.storage_service.write_chunk_artifact(job_id, index, chunk)

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
                chunk_count=len(chunks),
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
            await self.job_service.heartbeat_job(session, job_id, stage=stage)
            await session.commit()

    async def _mark_job_succeeded(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
        *,
        result: StyleAnalysisPipelineResult,
    ) -> None:
        async with session_factory() as session:
            await self.job_service.mark_job_succeeded(session, job_id, result=result)
            await session.commit()

    async def _mark_job_failed(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
        *,
        error_message: str,
    ) -> None:
        async with session_factory() as session:
            await self.job_service.mark_job_failed(session, job_id, error_message=error_message)
            await session.commit()

    async def _delete_checkpointer_thread(self, job_id: str) -> None:
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
        max_poll_interval_seconds: float | None = None,
    ) -> None:
        max_poll_interval_seconds = max_poll_interval_seconds or poll_interval_seconds
        current_interval = poll_interval_seconds
        while True:
            processed = await self.process_next_pending(session_factory)
            if processed:
                current_interval = poll_interval_seconds
                continue
            await asyncio.sleep(current_interval)
            current_interval = min(max_poll_interval_seconds, current_interval * 2)

    async def fail_stale_running_jobs(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        stale_after_seconds: int,
    ) -> None:
        async with session_factory() as session:
            await self.job_service.recover_stale_jobs(
                session,
                stale_after_seconds=stale_after_seconds,
                max_attempts=get_settings().style_analysis_max_attempts,
            )
            await session.commit()
