from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, NotRequired, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.db.models import ProviderConfig
from app.schemas.style_analysis_jobs import (
    AnalysisMeta,
    ChunkAnalysis,
    MergedAnalysis,
    STYLE_ANALYSIS_JOB_STAGE_AGGREGATING,
    STYLE_ANALYSIS_JOB_STAGE_ANALYZING_CHUNKS,
    STYLE_ANALYSIS_JOB_STAGE_POSTPROCESSING,
    STYLE_ANALYSIS_JOB_STAGE_REPORTING,
)
from app.services.style_analysis_llm import MarkdownLLMClient
from app.services.style_analysis_prompts import (
    build_chunk_analysis_prompt,
    build_merge_prompt,
    build_prompt_pack_prompt,
    build_report_prompt,
    build_style_summary_prompt,
)
from app.services.style_analysis_storage import StyleAnalysisStorageService
from app.services.style_analysis_text import InputClassification

logger = logging.getLogger(__name__)


class StyleAnalysisPauseRequested(Exception):
    pass


# -----------------------------------------------------------------------------
# 状态定义：LangGraph 工作流运行时的状态载体
# -----------------------------------------------------------------------------


class StyleAnalysisState(TypedDict):
    """流水线各节点共享的状态字典；NotRequired 字段在后续节点中逐步填充。"""

    job_id: str
    style_name: str
    source_filename: str
    model_name: str
    chunk_count: int
    classification: InputClassification

    merged_analysis_markdown: NotRequired[str]
    analysis_report_markdown: NotRequired[str]
    style_summary_markdown: NotRequired[str]
    prompt_pack_markdown: NotRequired[str]
    analysis_meta: NotRequired[dict[str, Any]]


class ChunkMapState(TypedDict):
    """Map 阶段每个并行任务的独立状态；避免共享大状态在并行任务间复制。"""

    job_id: str
    style_name: str
    model_name: str
    chunk_index: int
    chunk_count: int
    classification: InputClassification


# -----------------------------------------------------------------------------
# 结果定义：流水线执行完成后的最终输出结构
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class StyleAnalysisPipelineResult:
    analysis_meta: AnalysisMeta
    analysis_report_markdown: str
    style_summary_markdown: str
    prompt_pack_markdown: str


# 阶段切换回调：流水线进入新阶段时触发，用于更新 DB 里的 job.stage
StageCallback = Callable[[str | None], Awaitable[None]]


# -----------------------------------------------------------------------------
# 核心流水线：基于 LangGraph 的 MapReduce 风格分析引擎
# -----------------------------------------------------------------------------


class StyleAnalysisPipeline:
    """基于 LangGraph 状态机 + MapReduce 架构的风格分析流水线。

    执行流程：
    prepare_input → [并行 N 个 analyze_chunk] → merge_chunks →
    build_report → build_summary → build_prompt_pack → persist_result

    特性：
    - 可并行的分块深度分析
    - 通过 Checkpointer 支持中断恢复
    - 通过 MarkdownLLMClient 保证 Markdown 优先输出
    - 阶段切换回调用于实时展示进度
    """

    def __init__(
        self,
        *,
        provider: ProviderConfig,
        model_name: str,
        style_name: str,
        source_filename: str,
        llm_client: MarkdownLLMClient | None = None,
        checkpointer: Any | None = None,
        stage_callback: StageCallback | None = None,
        should_pause: Callable[[], bool] | None = None,
    ) -> None:
        self.provider = provider
        self.model_name = model_name
        self.style_name = style_name
        self.source_filename = source_filename

        self.llm_client = llm_client or MarkdownLLMClient()
        self.chat_model = self.llm_client.build_model(
            provider=provider, model_name=model_name
        )

        if checkpointer is None:
            logger.warning(
                "StyleAnalysisPipeline falling back to in-memory checkpointer; "
                "resume across process restarts will be lost.",
            )
            self.checkpointer = InMemorySaver()
        else:
            self.checkpointer = checkpointer

        self.stage_callback = stage_callback
        self.should_pause = should_pause

        self.storage_service = StyleAnalysisStorageService()

        self.graph = self._build_graph()

    async def run(
        self,
        *,
        job_id: str,
        chunk_count: int,
        classification: InputClassification,
        max_concurrency: int,
    ) -> StyleAnalysisPipelineResult:
        """Run the pipeline; resumes from checkpoint if one exists for ``job_id``."""
        initial_state: StyleAnalysisState = {
            "job_id": job_id,
            "style_name": self.style_name,
            "source_filename": self.source_filename,
            "model_name": self.model_name,
            "chunk_count": chunk_count,
            "classification": classification,
        }

        # LangGraph 运行配置
        config = {
            "configurable": {
                "thread_id": job_id
            },  # thread_id 必须与 job_id 一致，用于 checkpoint 寻址
            "max_concurrency": max_concurrency,  # 控制 Map 阶段的并行度
        }

        # 检查是否已有 checkpoint 存在
        checkpoint_state = await self.graph.aget_state(config)

        # 如果有未完成的节点（checkpoint_state.next 非空），则从断点继续，否则从头开始
        graph_input = None if checkpoint_state.next else initial_state

        # 启动状态机执行，直到所有节点完成
        final_state = await self.graph.ainvoke(graph_input, config)

        # 通知回调流水线已完成
        await self._set_stage(None)

        # 反序列化最终状态中的所有产物，返回给调用方
        return StyleAnalysisPipelineResult(
            analysis_meta=AnalysisMeta.model_validate(final_state["analysis_meta"]),
            analysis_report_markdown=str(final_state["analysis_report_markdown"]),
            style_summary_markdown=str(final_state["style_summary_markdown"]),
            prompt_pack_markdown=str(final_state["prompt_pack_markdown"]),
        )

    def _build_graph(self):
        """构建 LangGraph 状态图：并行 chunk 分析 → Reduce 聚合 → 线性下游。"""
        builder = StateGraph(StyleAnalysisState)

        builder.add_node("prepare_input", self._prepare_input)
        builder.add_node("analyze_chunk", self._analyze_chunk)
        builder.add_node("merge_chunks", self._merge_chunks)
        builder.add_node("build_report", self._build_report)
        builder.add_node("build_summary", self._build_summary)
        builder.add_node("build_prompt_pack", self._build_prompt_pack)
        builder.add_node("persist_result", self._persist_result)

        builder.add_edge(START, "prepare_input")
        # prepare_input 完成后动态生成 N 个 analyze_chunk 并行任务
        builder.add_conditional_edges(
            "prepare_input", self._route_chunks, ["analyze_chunk"]
        )
        builder.add_edge("analyze_chunk", "merge_chunks")
        builder.add_edge("merge_chunks", "build_report")
        builder.add_edge("build_report", "build_summary")
        builder.add_edge("build_summary", "build_prompt_pack")
        builder.add_edge("build_prompt_pack", "persist_result")
        builder.add_edge("persist_result", END)

        return builder.compile(checkpointer=self.checkpointer)

    async def _prepare_input(self, state: StyleAnalysisState) -> dict[str, Any]:
        """Entry node: validate chunk count and mark analyzing stage."""
        self._raise_if_paused()
        if state["chunk_count"] < 1:
            raise RuntimeError("切片后没有可分析的有效文本")

        await self._set_stage(STYLE_ANALYSIS_JOB_STAGE_ANALYZING_CHUNKS)
        await self.storage_service.append_job_log(
            state["job_id"],
            f"[System] 开始分析任务，共分为 {state['chunk_count']} 个文本分块进行并发处理..."
        )
        return {}

    def _route_chunks(self, state: StyleAnalysisState) -> list[Send]:
        """Fan out N parallel analyze_chunk tasks via LangGraph Send primitives."""
        self._raise_if_paused()
        MAX_CHUNKS = 1000
        if state["chunk_count"] > MAX_CHUNKS:
            raise ValueError(f"切片数量超过上限 ({MAX_CHUNKS})，可能导致内存溢出或超负荷，请更换较小样本或增加切分阈值。")
        return [
            Send(
                "analyze_chunk",
                {
                    "job_id": state["job_id"],
                    "style_name": state["style_name"],
                    "model_name": state["model_name"],
                    "chunk_index": index,
                    "chunk_count": state["chunk_count"],
                    "classification": state["classification"],
                },
            )
            for index in range(state["chunk_count"])
        ]

    async def _analyze_chunk(self, state: ChunkMapState) -> dict[str, Any]:
        """Map stage: analyze a single chunk; results persisted to storage, not shared state."""
        self._raise_if_paused()
        await self.storage_service.append_job_log(
            state["job_id"],
            f"[LLM] 正在并行处理 分块 {state['chunk_index'] + 1}/{state['chunk_count']} ..."
        )
        if self.storage_service.chunk_analysis_artifact_exists(
            state["job_id"], state["chunk_index"]
        ):
            return {}
        chunk = await self.storage_service.read_chunk_artifact(
            state["job_id"], state["chunk_index"]
        )

        prompt = build_chunk_analysis_prompt(
            chunk=chunk,
            chunk_index=state["chunk_index"],
            classification=state["classification"],
            chunk_count=state["chunk_count"],
        )

        self._raise_if_paused()
        markdown = await self.llm_client.ainvoke_markdown(
            model=self.chat_model,
            prompt=prompt,
            provider=self.provider,
            model_name=self.model_name,
        )

        # 将分析结果写入存储，供后续 merge 阶段读取
        await self.storage_service.write_chunk_analysis_artifact(
            state["job_id"],
            state["chunk_index"],
            ChunkAnalysis(
                chunk_index=state["chunk_index"],
                chunk_count=state["chunk_count"],
                markdown=markdown,
            ).model_dump(mode="json"),
        )

        await self.storage_service.append_job_log(
            state["job_id"],
            f"[LLM] 分块 {state['chunk_index'] + 1}/{state['chunk_count']} 分析完成"
        )
        # 不返回任何数据到共享状态，所有中间结果通过存储传递
        return {}

    async def _merge_chunks(self, state: StyleAnalysisState) -> dict[str, Any]:
        """Reduce stage: incrementally merge chunk analyses into a single document.

        Batching prevents a single oversized prompt; checkpointer persists
        intermediate merged state for resume.
        """
        self._raise_if_paused()
        await self._set_stage(STYLE_ANALYSIS_JOB_STAGE_AGGREGATING)
        await self.storage_service.append_job_log(
            state["job_id"],
            f"[LangGraph] 正在执行 Reduce 聚合操作 (合并 {state['chunk_count']} 个分块的结果)..."
        )

        if self.storage_service.stage_markdown_artifact_exists(
            state["job_id"], name="merged-analysis"
        ):
            markdown = await self.storage_service.read_stage_markdown_artifact(
                state["job_id"], name="merged-analysis"
            )
            return {"merged_analysis_markdown": markdown}

        merged: MergedAnalysis | None = None

        # 分批读取所有 chunk 的分析结果，每批最多 20 个
        batch_index = 0
        async for batch in self.storage_service.read_chunk_analysis_batches(
            state["job_id"],
            batch_size=20,
        ):
            self._raise_if_paused()
            batch_index += 1
            # 按 chunk 索引排序，保证合并顺序正确
            chunk_analyses = sorted(
                (ChunkAnalysis.model_validate(item) for item in batch),
                key=lambda item: item.chunk_index,
            )

            # 边界情况：只有一个 chunk 时不需要合并，直接使用
            if merged is None and len(chunk_analyses) == 1:
                merged = MergedAnalysis(
                    classification=state["classification"],
                    markdown=chunk_analyses[0].markdown,
                )
                continue

            start_idx = chunk_analyses[0].chunk_index + 1
            end_idx = chunk_analyses[-1].chunk_index + 1
            await self.storage_service.append_job_log(
                state["job_id"],
                f"[LLM] 正在合并批次 {batch_index} (涵盖分块 {start_idx} 到 {end_idx})..."
            )

            # 构建合并输入：当前批次的 chunk 分析 + 之前合并的结果
            merge_inputs = [item.model_dump(mode="json") for item in chunk_analyses]
            if merged is not None:
                merge_inputs.insert(0, merged.model_dump(mode="json"))

            self._raise_if_paused()
            markdown = await self.llm_client.ainvoke_markdown(
                model=self.chat_model,
                prompt=build_merge_prompt(
                    chunk_analyses=merge_inputs,
                    classification=state["classification"],
                ),
                provider=self.provider,
                model_name=self.model_name,
            )
            merged = MergedAnalysis(
                classification=state["classification"],
                markdown=markdown,
            )
            
            await self.storage_service.append_job_log(
                state["job_id"],
                f"[LLM] 批次 {batch_index} 合并完成"
            )

        if merged is None:
            raise RuntimeError("聚合阶段没有读到任何 chunk 分析结果")

        await self.storage_service.write_stage_markdown_artifact(
            state["job_id"], name="merged-analysis", markdown=merged.markdown
        )
        # 将合并结果写入共享状态，供后续阶段使用
        return {"merged_analysis_markdown": merged.markdown}

    async def _build_report(self, state: StyleAnalysisState) -> dict[str, Any]:
        """Build the full multi-dimensional analysis report from merged chunks."""
        self._raise_if_paused()
        await self._set_stage(STYLE_ANALYSIS_JOB_STAGE_REPORTING)
        await self.storage_service.append_job_log(
            state["job_id"],
            "[System] 正在生成最终 Markdown 报告..."
        )

        if self.storage_service.stage_markdown_artifact_exists(
            state["job_id"], name="analysis-report"
        ):
            markdown = await self.storage_service.read_stage_markdown_artifact(
                state["job_id"], name="analysis-report"
            )
            return {"analysis_report_markdown": markdown}

        report_markdown = await self.llm_client.ainvoke_markdown(
            model=self.chat_model,
            prompt=build_report_prompt(
                merged_analysis_markdown=state["merged_analysis_markdown"],
                classification=state["classification"],
            ),
            provider=self.provider,
            model_name=self.model_name,
        )

        await self.storage_service.write_stage_markdown_artifact(
            state["job_id"], name="analysis-report", markdown=report_markdown
        )
        return {"analysis_report_markdown": report_markdown}

    async def _build_summary(self, state: StyleAnalysisState) -> dict[str, Any]:
        """Distill the style summary (精简的风格特征) from the report."""
        self._raise_if_paused()
        await self._set_stage(STYLE_ANALYSIS_JOB_STAGE_POSTPROCESSING)
        await self.storage_service.append_job_log(
            state["job_id"],
            "[System] 正在提炼风格特征，生成摘要..."
        )

        if self.storage_service.stage_markdown_artifact_exists(
            state["job_id"], name="style-summary"
        ):
            markdown = await self.storage_service.read_stage_markdown_artifact(
                state["job_id"], name="style-summary"
            )
            return {"style_summary_markdown": markdown}

        summary_markdown = await self.llm_client.ainvoke_markdown(
            model=self.chat_model,
            prompt=build_style_summary_prompt(
                report_markdown=state["analysis_report_markdown"],
                style_name=state["style_name"],
            ),
            provider=self.provider,
            model_name=self.model_name,
        )

        stripped = summary_markdown.lstrip()
        if not stripped.startswith("# 风格名称"):
            expected_title = f"# {state['style_name']}"
            if stripped.startswith(expected_title):
                remainder = stripped[len(expected_title) :].lstrip("\n")
                summary_markdown = f"# 风格名称\n{state['style_name']}\n\n{remainder}".rstrip()
            else:
                summary_markdown = (
                    f"# 风格名称\n{state['style_name']}\n\n{summary_markdown}".rstrip()
                )

        await self.storage_service.write_stage_markdown_artifact(
            state["job_id"], name="style-summary", markdown=summary_markdown
        )
        return {"style_summary_markdown": summary_markdown}

    async def _build_prompt_pack(self, state: StyleAnalysisState) -> dict[str, Any]:
        """Compose the final prompt pack combining report and summary."""
        self._raise_if_paused()
        await self._set_stage(STYLE_ANALYSIS_JOB_STAGE_POSTPROCESSING)
        await self.storage_service.append_job_log(
            state["job_id"],
            "[System] 正在构建最终的母 Prompt 包..."
        )

        if self.storage_service.stage_markdown_artifact_exists(
            state["job_id"], name="prompt-pack"
        ):
            markdown = await self.storage_service.read_stage_markdown_artifact(
                state["job_id"], name="prompt-pack"
            )
            return {"prompt_pack_markdown": markdown}

        prompt_pack_markdown = await self.llm_client.ainvoke_markdown(
            model=self.chat_model,
            prompt=build_prompt_pack_prompt(
                report_markdown=state["analysis_report_markdown"],
                style_summary_markdown=state["style_summary_markdown"],
            ),
            provider=self.provider,
            model_name=self.model_name,
        )

        await self.storage_service.write_stage_markdown_artifact(
            state["job_id"], name="prompt-pack", markdown=prompt_pack_markdown
        )
        return {"prompt_pack_markdown": prompt_pack_markdown}

    async def _persist_result(self, state: StyleAnalysisState) -> dict[str, Any]:
        """Assemble analysis metadata; no external IO."""
        self._raise_if_paused()
        await self.storage_service.append_job_log(
            state["job_id"],
            "[System] 分析任务全部完成！"
        )
        analysis_meta = AnalysisMeta(
            source_filename=state["source_filename"],
            model_name=state["model_name"],
            text_type=state["classification"]["text_type"],
            has_timestamps=state["classification"]["has_timestamps"],
            has_speaker_labels=state["classification"]["has_speaker_labels"],
            has_noise_markers=state["classification"]["has_noise_markers"],
            uses_batch_processing=state["classification"]["uses_batch_processing"],
            location_indexing=state["classification"]["location_indexing"],
            chunk_count=state["chunk_count"],
        )

        return {"analysis_meta": analysis_meta.model_dump(mode="json")}

    async def _set_stage(self, stage: str | None) -> None:
        """Trigger the stage-change callback (``stage=None`` signals completion)."""
        self._raise_if_paused()
        if self.stage_callback is not None:
            await self.stage_callback(stage)

    def _raise_if_paused(self) -> None:
        if self.should_pause is not None and self.should_pause():
            raise StyleAnalysisPauseRequested()
