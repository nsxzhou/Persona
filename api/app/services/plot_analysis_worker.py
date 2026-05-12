from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import ClassVar, cast

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.db.models import ProviderConfig
from app.schemas.plot_analysis_jobs import PLOT_ANALYSIS_JOB_STAGE_PREPARING_INPUT
from app.services.checkpointer_factory import PlotAnalysisCheckpointerFactory
from app.services.plot_analysis_jobs import PlotAnalysisJobService
from app.services.plot_analysis_pipeline import (
    PlotAnalysisPauseRequested,
    PlotAnalysisPipeline,
    PlotAnalysisPipelineResult,
)
from app.services.analysis_worker_lifecycle import (
    BaseAnalysisJobExecutor,
    ShouldPause,
    StageCallback,
)
from app.core.text_processing import InputClassification
from app.services.llm_provider import LLMProviderService
from app.services.plot_analysis_storage import PlotAnalysisStorageService
from app.services.plot_analysis_text import PlotBoundaryDetector, read_plot_chunks_and_classification

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlotAnalysisRunContext:
    provider: ProviderConfig
    plot_name: str
    model_name: str
    source_filename: str
    chunk_count: int
    classification: InputClassification


class PlotAnalysisJobExecutor(BaseAnalysisJobExecutor):
    job_service: PlotAnalysisJobService
    checkpointer_factory: PlotAnalysisCheckpointerFactory
    storage_service: PlotAnalysisStorageService
    initial_stage: ClassVar[str | None] = PLOT_ANALYSIS_JOB_STAGE_PREPARING_INPUT
    pause_exceptions: ClassVar[tuple[type[BaseException], ...]] = (
        PlotAnalysisPauseRequested,
    )
    failure_log_message: ClassVar[str] = "plot analysis job failed"
    heartbeat_failure_log_message: ClassVar[str] = (
        "Failed to send periodic plot analysis heartbeat"
    )
    logger: ClassVar[logging.Logger] = logger

    def __init__(self) -> None:
        job_service = PlotAnalysisJobService()
        checkpointer_factory = PlotAnalysisCheckpointerFactory()
        storage_service = PlotAnalysisStorageService()
        super().__init__(
            job_service=job_service,
            checkpointer_factory=checkpointer_factory,
            storage_service=storage_service,
            worker_id_prefix="plot-worker",
        )
        self.job_service = job_service
        self.checkpointer_factory = checkpointer_factory
        self.storage_service = storage_service

    def _max_attempts(self) -> int:
        return get_settings().plot_analysis_max_attempts

    def _stale_timeout_seconds(self) -> int:
        return get_settings().plot_analysis_stale_timeout_seconds

    async def _run_job_to_success(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
        *,
        stage_callback: StageCallback,
        should_pause: ShouldPause,
    ) -> None:
        context = await self._load_run_context(session_factory, job_id)
        pipeline = await self._build_pipeline(
            provider=context.provider,
            model_name=context.model_name,
            plot_name=context.plot_name,
            source_filename=context.source_filename,
            stage_callback=stage_callback,
            should_pause=should_pause,
        )
        max_concurrency = max(
            1,
            min(get_settings().plot_analysis_chunk_max_concurrency, 32),
        )
        result = await pipeline.run(
            job_id=job_id,
            chunk_count=context.chunk_count,
            classification=context.classification,
            max_concurrency=max_concurrency,
        )
        await self._mark_job_succeeded(session_factory, job_id, result=result)

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
        llm_service = LLMProviderService()

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
            raw = await llm_service.invoke_markdown_completion(
                provider_config=provider,
                prompt=prompt,
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
        stage_callback: Callable[[str | None], Awaitable[None]],
        should_pause: Callable[[], bool] | None = None,
    ) -> PlotAnalysisPipeline:
        llm_service = LLMProviderService()
        return PlotAnalysisPipeline(
            provider=provider,
            model_name=model_name,
            plot_name=plot_name,
            source_filename=source_filename,
            llm_service=llm_service,
            checkpointer=await self.checkpointer_factory.get(),
            storage_service=self.storage_service,
            stage_callback=stage_callback,
            should_pause=should_pause,
        )

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
                story_engine_payload=result.story_engine_markdown,
                plot_skeleton_payload=result.plot_skeleton_markdown,
            )
            await session.commit()

PlotAnalysisWorkerService = PlotAnalysisJobExecutor
