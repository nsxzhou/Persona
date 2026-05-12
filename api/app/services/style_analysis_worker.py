from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import ClassVar
from typing import cast

# SQLAlchemy 异步会话：用于数据库读写（claim/heartbeat/写回结果等）
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# 配置读取：统一从环境变量/配置文件中获取运行参数（并发、超时、重试次数等）
from app.core.config import get_settings
# ProviderConfig：LLM 提供商配置模型（base_url、api_key 等），供 pipeline 初始化模型使用
from app.db.models import ProviderConfig
# 任务阶段常量：用于 worker 在“准备输入”阶段标记 job.stage
from app.schemas.style_analysis_jobs import STYLE_ANALYSIS_JOB_STAGE_PREPARING_INPUT
# Checkpointer 工厂：LangGraph 断点续跑/恢复用的 checkpointer 生成器（sqlite/postgres/memory）
from app.services.style_analysis_checkpointer import StyleAnalysisCheckpointerFactory
# JobService：封装分析任务的状态流转（claim、heartbeat、成功/失败写回）
from app.services.style_analysis_jobs import StyleAnalysisJobService
# Pipeline：风格分析主流程（切块分析→聚合→报告→摘要→prompt pack）
from app.services.style_analysis_pipeline import (
    StyleAnalysisPipeline,
    StyleAnalysisPauseRequested,
    StyleAnalysisPipelineResult,
)
from app.services.analysis_worker_lifecycle import (
    BaseAnalysisJobExecutor,
    ShouldPause,
    StageCallback,
)
# StorageService：样本文本流式读取、chunk/分析产物落盘、任务结束后清理
from app.services.style_analysis_storage import StyleAnalysisStorageService
# 文本处理：负责对 TXT 做切块并推断输入类型（是否时间戳/说话人/噪声等）
from app.core.text_processing import InputClassification, read_chunks_and_classification

# 模块级 logger：统一日志入口，便于在 worker 中记录异常与关键运行信息
logger = logging.getLogger(__name__)


# 运行上下文：worker 在真正跑 pipeline 前，从数据库与样本文本中整理出的必要信息集合
# 该结构是不可变的（frozen=True），便于在 pipeline 执行过程中安全传递/复用
@dataclass(frozen=True)
class StyleAnalysisRunContext:
    # provider：当前 job 绑定的 LLM 提供商配置
    provider: ProviderConfig
    # style_name：风格名称（展示/持久化用）
    style_name: str
    # model_name：本次分析使用的模型名称
    model_name: str
    # source_filename：用户上传的原始文件名（用于元数据记录）
    source_filename: str
    # chunk_count：切片数量（决定 pipeline map 阶段的任务个数）
    chunk_count: int
    # classification：对输入文本结构的判定结果（字幕/正文等），会影响 prompt 与报告内容
    classification: InputClassification


class StyleAnalysisJobExecutor(BaseAnalysisJobExecutor):
    job_service: StyleAnalysisJobService
    checkpointer_factory: StyleAnalysisCheckpointerFactory
    storage_service: StyleAnalysisStorageService
    initial_stage: ClassVar[str | None] = STYLE_ANALYSIS_JOB_STAGE_PREPARING_INPUT
    pause_exceptions: ClassVar[tuple[type[BaseException], ...]] = (
        StyleAnalysisPauseRequested,
    )
    failure_log_message: ClassVar[str] = "style analysis job failed"
    heartbeat_failure_log_message: ClassVar[str] = (
        "Failed to send periodic style analysis heartbeat"
    )
    logger: ClassVar[logging.Logger] = logger

    def __init__(self) -> None:
        job_service = StyleAnalysisJobService()
        checkpointer_factory = StyleAnalysisCheckpointerFactory()
        storage_service = StyleAnalysisStorageService()
        super().__init__(
            job_service=job_service,
            checkpointer_factory=checkpointer_factory,
            storage_service=storage_service,
            worker_id_prefix="style-worker",
        )
        self.job_service = job_service
        self.checkpointer_factory = checkpointer_factory
        self.storage_service = storage_service

    def _max_attempts(self) -> int:
        return get_settings().style_analysis_max_attempts

    def _stale_timeout_seconds(self) -> int:
        return get_settings().style_analysis_stale_timeout_seconds

    async def _run_job_to_success(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
        *,
        stage_callback: StageCallback,
        should_pause: ShouldPause,
    ) -> None:
        # 读取 job + 样本文本，并把文本切块落盘，得到 pipeline 运行所需上下文
        context = await self._load_run_context(session_factory, job_id)
        # 基于 provider/model/style/source 构造 pipeline（含 checkpointer 与阶段回调）
        pipeline = await self._build_pipeline(
            provider=context.provider,
            model_name=context.model_name,
            style_name=context.style_name,
            source_filename=context.source_filename,
            stage_callback=stage_callback,
            should_pause=should_pause,
        )
        # 任务并发度：用于控制 chunk 分析阶段的并发上限（避免过高并发打爆模型/网络）
        max_concurrency = max(
            1,
            min(get_settings().style_analysis_chunk_max_concurrency, 32),
        )
        # 运行主流程，产出结构化结果（analysis_meta/report/voice_profile）
        result = await pipeline.run(
            job_id=job_id,
            chunk_count=context.chunk_count,
            classification=context.classification,
            max_concurrency=max_concurrency,
        )
        # 成功写回：更新 payload、状态、清理锁与完成时间
        await self._mark_job_succeeded(session_factory, job_id, result=result)

    # 加载运行上下文：
    # - 读取 job 信息（包含 sample_file、provider 等关联数据）
    # - 将样本文本按 chunk_size 切片落盘，供 pipeline 逐块读取
    # - 计算 character_count 并回写到 sample_file，用于统计/展示
    # - 同时推断输入文本分类（字幕/正文、多说话人、噪声等）
    async def _load_run_context(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
    ) -> StyleAnalysisRunContext:
        async with session_factory() as session:
            # 获取任务基础信息（找不到则抛出 404 领域错误）
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
                        return StyleAnalysisRunContext(
                            provider=job.provider,
                            style_name=job.style_name,
                            model_name=job.model_name,
                            source_filename=job.sample_file.original_filename,
                            chunk_count=existing_chunk_count,
                            classification=cast(InputClassification, classification),
                        )

            # 持久化单个 chunk：将切片内容写入本地存储，后续 pipeline 会按索引读取
            async def persist_chunk(index: int, chunk_text: str) -> None:
                await self.storage_service.write_chunk_artifact(job_id, index, chunk_text)

            # 读样本文件流并切块，同时做输入分类与字符统计
            chunk_count, character_count, base_classification = await read_chunks_and_classification(
                self.storage_service.stream_file(job.sample_file.id),
                on_chunk=persist_chunk if existing_chunk_count == 0 else None,
            )
            if existing_chunk_count and chunk_count != existing_chunk_count:
                raise RuntimeError("检测到已存在的切片与当前切片规则不一致，请删除任务后重试")

            # 没有任何有效切片：直接视为不可分析输入
            if chunk_count < 1:
                raise RuntimeError("切片后没有可分析的有效文本")

            # uses_batch_processing：由 worker 根据切片数量补充，后续会影响提示词与报告表述
            classification: InputClassification = {
                **base_classification,
                "uses_batch_processing": chunk_count > 1,
            }
            # 回写字符统计（用于任务详情展示/费用估算等）
            job.sample_file.character_count = character_count
            await session.commit()
            await self.storage_service.write_json_artifact(
                job_id,
                name="input-classification",
                payload={
                    "character_count": character_count,
                    "classification": classification,
                },
            )
            # 组装不可变上下文，供 pipeline 执行
            return StyleAnalysisRunContext(
                provider=job.provider,
                style_name=job.style_name,
                model_name=job.model_name,
                source_filename=job.sample_file.original_filename,
                chunk_count=chunk_count,
                classification=classification,
            )

    # 构建 pipeline：
    # - 注入 provider/model/style/source
    # - 通过 checkpointer_factory 获取持久化 checkpointer（用于断点续跑）
    # - 注入 stage_callback，在 pipeline 内部切换阶段时同步到 job.stage
    async def _build_pipeline(
        self,
        *,
        provider: ProviderConfig,
        model_name: str,
        style_name: str,
        source_filename: str,
        stage_callback: Callable[[str | None], Awaitable[None]],
        should_pause: Callable[[], bool] | None = None,
    ) -> StyleAnalysisPipeline:
        return StyleAnalysisPipeline(
            provider=provider,
            model_name=model_name,
            style_name=style_name,
            source_filename=source_filename,
            checkpointer=await self.checkpointer_factory.get(),
            stage_callback=stage_callback,
            should_pause=should_pause,
        )

    # 标记任务成功：写入结构化结果 payload，并更新状态/完成时间等字段
    async def _mark_job_succeeded(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
        *,
        result: StyleAnalysisPipelineResult,
    ) -> None:
        async with session_factory() as session:
            await self.job_service.mark_job_succeeded(
                session,
                job_id,
                analysis_meta_payload=result.analysis_meta.model_dump(mode="json"),
                analysis_report_payload=result.analysis_report_markdown,
                voice_profile_payload=result.voice_profile_markdown,
            )
            await session.commit()


# Public alias — preserves historical import path.
StyleAnalysisWorkerService = StyleAnalysisJobExecutor
