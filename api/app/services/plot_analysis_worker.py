from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.db.models import ProviderConfig
from app.schemas.plot_analysis_jobs import PLOT_ANALYSIS_JOB_STAGE_PREPARING_INPUT
from app.services.plot_analysis_checkpointer import PlotAnalysisCheckpointerFactory
from app.services.plot_analysis_jobs import PlotAnalysisJobService
from app.services.plot_analysis_pipeline import (
    PlotAnalysisPauseRequested,
    PlotAnalysisPipeline,
    PlotAnalysisPipelineResult,
)
from app.services.plot_analysis_storage import PlotAnalysisStorageService
from app.services.plot_analysis_text import PlotBoundaryDetector, read_plot_chunks_and_classification
from app.services.style_analysis_llm import MarkdownLLMClient
from app.services.style_analysis_text import InputClassification

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlotAnalysisRunContext:
    provider: ProviderConfig
    plot_name: str
    model_name: str
    source_filename: str
    chunk_count: int
    classification: InputClassification


class PlotAnalysisJobExecutor:
    def __init__(self) -> None:
        self.job_service = PlotAnalysisJobService()
        self.checkpointer_factory = PlotAnalysisCheckpointerFactory()
        self.storage_service = PlotAnalysisStorageService()
        self._pause_events: dict[str, asyncio.Event] = {}
        self._worker_id = f"plot-worker-{uuid.uuid4()}"

    async def aclose(self) -> None:
        await self.checkpointer_factory.aclose()

    async def process_next_pending(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> bool:
        worker_id = self._worker_id
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
        async with session_factory.begin() as session:
            candidate_id = await self.job_service.claim_job_for_worker(
                session,
                worker_id=worker_id,
                max_attempts=settings.style_analysis_max_attempts,
            )
            return candidate_id

    async def _run_claimed_job(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
    ) -> None:
        should_cleanup = False
        current_stage: str | None = PLOT_ANALYSIS_JOB_STAGE_PREPARING_INPUT
        pause_event = asyncio.Event()
        self._pause_events[job_id] = pause_event
        stop_heartbeat = asyncio.Event()
        heartbeat_task = asyncio.create_task(
            self._run_stage_heartbeat_loop(
                session_factory,
                job_id,
                get_stage=lambda: current_stage,
                stop_event=stop_heartbeat,
                interval_seconds=self._heartbeat_interval_seconds(),
            )
        )

        async def stage_callback(stage: str | None) -> None:
            nonlocal current_stage
            current_stage = stage
            await self._touch_job_stage(
                session_factory,
                job_id,
                stage=stage,
            )

        try:
            context = await self._load_run_context(session_factory, job_id)
            pipeline = await self._build_pipeline(
                provider=context.provider,
                model_name=context.model_name,
                plot_name=context.plot_name,
                source_filename=context.source_filename,
                stage_callback=stage_callback,
                should_pause=pause_event.is_set,
            )
            max_concurrency = max(
                1,
                min(get_settings().style_analysis_chunk_max_concurrency, 32),
            )
            result = await pipeline.run(
                job_id=job_id,
                chunk_count=context.chunk_count,
                classification=context.classification,
                max_concurrency=max_concurrency,
            )
            await self._mark_job_succeeded(session_factory, job_id, result=result)
            should_cleanup = True
        except PlotAnalysisPauseRequested:
            await self._mark_job_paused(
                session_factory,
                job_id,
                stage=current_stage,
            )
        except Exception as exc:
            logger.exception(
                "plot analysis job failed",
                extra={"job_id": job_id},
            )
            await self._mark_job_failed(
                session_factory,
                job_id,
                error_message=str(exc),
            )
        finally:
            stop_heartbeat.set()
            await heartbeat_task
            self._pause_events.pop(job_id, None)
            if should_cleanup:
                await self.storage_service.cleanup_job_artifacts(job_id)
                await self._delete_checkpointer_thread(job_id)

    def _heartbeat_interval_seconds(self) -> float:
        stale_timeout_seconds = max(1, get_settings().style_analysis_stale_timeout_seconds)
        return max(0.2, min(30.0, stale_timeout_seconds / 3))

    async def _run_stage_heartbeat_loop(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
        *,
        get_stage: Callable[[], str | None],
        stop_event: asyncio.Event,
        interval_seconds: float,
    ) -> None:
        while not stop_event.is_set():
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
                break
            except TimeoutError:
                stage = get_stage()
                if stage is None:
                    continue
                try:
                    await self._touch_job_stage(
                        session_factory,
                        job_id,
                        stage=stage,
                    )
                except Exception:
                    logger.exception(
                        "Failed to send periodic plot analysis heartbeat",
                        extra={"job_id": job_id, "stage": stage},
                    )

    async def _load_run_context(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
    ) -> PlotAnalysisRunContext:
        async with session_factory() as session:
            job = await self.job_service.get_or_404(session, job_id)

            existing_chunk_count = (
                self.storage_service.count_chunk_artifacts(job_id)
                if self.storage_service.chunk_artifacts_exist(job_id)
                else 0
            )
            if existing_chunk_count > 0:
                if self.storage_service.json_artifact_exists(job_id, name="input-classification"):
                    payload = await self.storage_service.read_json_artifact(
                        job_id, name="input-classification"
                    )
                    persisted_character_count = payload.get("character_count")
                    if job.sample_file.character_count is None and isinstance(
                        persisted_character_count, int
                    ):
                        job.sample_file.character_count = persisted_character_count
                        await session.commit()
                    classification = payload.get("classification")
                    if isinstance(classification, dict):
                        return PlotAnalysisRunContext(
                            provider=job.provider,
                            plot_name=job.plot_name,
                            model_name=job.model_name,
                            source_filename=job.sample_file.original_filename,
                            chunk_count=existing_chunk_count,
                            classification=cast(InputClassification, classification),
                        )

            async def persist_chunk(index: int, chunk_text: str) -> None:
                await self.storage_service.write_chunk_artifact(job_id, index, chunk_text)

            chunk_count, character_count, base_classification, manifest = await read_plot_chunks_and_classification(
                self.storage_service.stream_file(job.sample_file.id),
                on_chunk=persist_chunk if existing_chunk_count == 0 else None,
                boundary_detector=self._build_boundary_detector(
                    provider=job.provider,
                    model_name=job.model_name,
                ),
            )
            if existing_chunk_count and chunk_count != existing_chunk_count:
                raise RuntimeError("检测到已存在的切片与当前切片规则不一致，请删除任务后重试")

            if chunk_count < 1:
                raise RuntimeError("切片后没有可分析的有效文本")

            classification: InputClassification = {
                **base_classification,
                "uses_batch_processing": chunk_count > 1,
            }
            job.sample_file.character_count = character_count
            await session.commit()
            if existing_chunk_count == 0:
                await self.storage_service.write_chunk_manifest(job_id, manifest)
            await self.storage_service.write_json_artifact(
                job_id,
                name="input-classification",
                payload={
                    "character_count": character_count,
                    "classification": classification,
                },
            )
            return PlotAnalysisRunContext(
                provider=job.provider,
                plot_name=job.plot_name,
                model_name=job.model_name,
                source_filename=job.sample_file.original_filename,
                chunk_count=chunk_count,
                classification=classification,
            )

    def _build_boundary_detector(
        self,
        *,
        provider: ProviderConfig,
        model_name: str,
    ) -> PlotBoundaryDetector | None:
        configured_model = (get_settings().plot_analysis_boundary_model or "").strip()
        if not configured_model:
            return None
        llm_client = MarkdownLLMClient()
        boundary_model = llm_client.build_model(provider=provider, model_name=configured_model)

        async def detect(paragraphs: list[str]) -> list[int] | None:
            prompt = (
                "你是 Plot Lab 的场景边界判定器。输入是一段超长连续正文的段落列表，请找出适合切分为多个叙事单元的边界。\n"
                "返回 JSON，且只能返回 JSON。格式：{\"boundaries\":[3,5]}。\n"
                "规则：\n"
                "- 边界索引表示“在第 N 段之后切开”，所以取值范围必须是 1 到 段落总数-1。\n"
                "- 只在明显的时间跳转、地点切换、视角转换、冲突阶段切换处切。\n"
                "- 如果没有明显边界，返回 {\"boundaries\":[]}。\n\n"
                f"段落总数：{len(paragraphs)}\n"
                f"段落列表：{json.dumps(paragraphs, ensure_ascii=False)}"
            )
            raw = await llm_client.ainvoke_markdown(
                model=boundary_model,
                prompt=prompt,
                provider=provider,
                model_name=configured_model,
                injection_mode="analysis",
            )
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Plot boundary detector returned invalid JSON")
                return None
            if isinstance(parsed, list):
                candidates = parsed
            elif isinstance(parsed, dict):
                candidates = parsed.get("boundaries")
            else:
                return None
            if not isinstance(candidates, list):
                return None
            return [candidate for candidate in candidates if isinstance(candidate, int)]

        return detect

    async def _build_pipeline(
        self,
        *,
        provider: ProviderConfig,
        model_name: str,
        plot_name: str,
        source_filename: str,
        stage_callback,
        should_pause=None,
    ) -> PlotAnalysisPipeline:
        llm_client = MarkdownLLMClient()
        chat_model = llm_client.build_model(provider=provider, model_name=model_name)
        return PlotAnalysisPipeline(
            provider=provider,
            model_name=model_name,
            plot_name=plot_name,
            source_filename=source_filename,
            llm_client=llm_client,
            chat_model=chat_model,
            checkpointer=await self.checkpointer_factory.get(),
            storage_service=self.storage_service,
            stage_callback=stage_callback,
            should_pause=should_pause,
        )

    async def _touch_job_stage(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
        *,
        stage: str | None,
    ) -> None:
        async with session_factory() as session:
            pause_requested_at = await self.job_service.heartbeat_job(
                session, job_id, stage=stage
            )
            await session.commit()
            if pause_requested_at is not None:
                pause_event = self._pause_events.get(job_id)
                if pause_event is not None:
                    pause_event.set()

    async def _mark_job_succeeded(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
        *,
        result: PlotAnalysisPipelineResult,
    ) -> None:
        async with session_factory() as session:
            await self.job_service.mark_job_succeeded(
                session,
                job_id,
                analysis_meta_payload=result.analysis_meta.model_dump(mode="json"),
                analysis_report_payload=result.analysis_report_markdown,
                plot_summary_payload=result.plot_summary_markdown,
                prompt_pack_payload=result.prompt_pack_markdown,
                plot_skeleton_payload=result.plot_skeleton_markdown,
            )
            await session.commit()

    async def _mark_job_failed(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
        *,
        error_message: str,
    ) -> bool:
        async with session_factory() as session:
            is_terminal = await self.job_service.mark_job_failed(
                session,
                job_id,
                error_message=error_message,
                max_attempts=get_settings().style_analysis_max_attempts,
            )
            await session.commit()
            return is_terminal

    async def _mark_job_paused(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
        *,
        stage: str | None,
    ) -> None:
        async with session_factory() as session:
            await self.job_service.mark_job_paused(session, job_id, stage=stage)
            await session.commit()

    async def _delete_checkpointer_thread(self, job_id: str) -> None:
        await self.checkpointer_factory.delete_thread(job_id)

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

    async def run_worker(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        poll_interval_seconds: float,
        max_poll_interval_seconds: float | None = None,
    ) -> None:
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be greater than 0")
        if max_poll_interval_seconds is not None and max_poll_interval_seconds <= 0:
            raise ValueError("max_poll_interval_seconds must be greater than 0")
        max_poll_interval_seconds = max_poll_interval_seconds or poll_interval_seconds
        if max_poll_interval_seconds < poll_interval_seconds:
            max_poll_interval_seconds = poll_interval_seconds

        settings = get_settings()
        last_stale_check = 0.0
        stale_check_interval = max(
            5.0,
            float(settings.style_analysis_stale_timeout_seconds) / 3.0,
        )
        current_interval = poll_interval_seconds
        while True:
            now = time.monotonic()
            if now - last_stale_check >= stale_check_interval:
                await self.fail_stale_running_jobs(
                    session_factory,
                    stale_after_seconds=settings.style_analysis_stale_timeout_seconds,
                )
                last_stale_check = now
            processed = await self.process_next_pending(session_factory)
            if processed:
                current_interval = poll_interval_seconds
                continue
            await asyncio.sleep(current_interval)
            current_interval = min(max_poll_interval_seconds, current_interval * 2)


PlotAnalysisWorkerService = PlotAnalysisJobExecutor
