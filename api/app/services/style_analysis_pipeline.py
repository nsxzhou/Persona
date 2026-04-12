# 未来语法导入：让 Python 支持更新的类型注解语法，兼容旧版本 Python
from __future__ import annotations

# collections.abc：类型注解用的 Callable（可调用对象）、Awaitable（可等待对象）
from collections.abc import Awaitable, Callable

# dataclasses：用于定义轻量不可变的数据结构（管道结果）
from dataclasses import dataclass

# typing：类型系统支持，NotRequired 表示状态字典中的可选字段
from typing import Any, NotRequired, TypedDict

# LangGraph 核心组件：用于构建可中断、可恢复、可并行的状态机工作流
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

# ProviderConfig：LLM 提供商配置模型（base_url、api_key 等）
from app.db.models import ProviderConfig

# 所有分析阶段的 Pydantic 模型定义与阶段常量
from app.schemas.style_analysis_jobs import (
    AnalysisMeta,
    ChunkAnalysis,
    MergedAnalysis,
    STYLE_ANALYSIS_JOB_STAGE_AGGREGATING,
    STYLE_ANALYSIS_JOB_STAGE_ANALYZING_CHUNKS,
    STYLE_ANALYSIS_JOB_STAGE_COMPOSING_PROMPT_PACK,
    STYLE_ANALYSIS_JOB_STAGE_REPORTING,
    STYLE_ANALYSIS_JOB_STAGE_SUMMARIZING,
)

# MarkdownLLMClient：Markdown 优先输出 LLM 客户端，保证输出符合 Markdown 格式要求
from app.services.style_analysis_llm import MarkdownLLMClient

# 所有阶段的 Prompt 构建函数，集中管理提示词模板
from app.services.style_analysis_prompts import (
    build_chunk_analysis_prompt,
    build_merge_prompt,
    build_prompt_pack_prompt,
    build_report_prompt,
    build_style_summary_prompt,
)

# 存储服务：负责 chunk 文本、分析中间产物的读写与批量读取
from app.services.style_analysis_storage import StyleAnalysisStorageService

# InputClassification：文本分类结果（文本类型、是否有时间戳、说话人标签等）
from app.services.style_analysis_text import InputClassification


# -----------------------------------------------------------------------------
# 状态定义层：LangGraph 工作流运行时的状态载体
# -----------------------------------------------------------------------------

"""
StyleAnalysisState 是整个分析流水线的共享状态字典，在所有节点间传递
采用 TypedDict 定义而非 dataclass，是为了兼容 LangGraph 的状态序列化机制
NotRequired 标记的字段表示在流程早期阶段可能不存在，会在后续节点中逐步填充
"""


class StyleAnalysisState(TypedDict):
    job_id: str  # 分析任务唯一标识，作为 checkpointer 的 thread_id
    style_name: str  # 用户指定的风格名称
    source_filename: str  # 原始上传文件名，用于元数据记录
    model_name: str  # 本次分析使用的 LLM 模型名称
    chunk_count: int  # 文本切块总数，决定 Map 阶段的并行任务数
    classification: InputClassification  # 文本分类结果，影响所有阶段的 Prompt 生成

    # 以下字段会在流水线执行过程中逐步生成并填充到状态中
    merged_analysis_markdown: NotRequired[str]  # 多 chunk 聚合后的完整 markdown 分析
    analysis_report_markdown: NotRequired[str]  # 最终 markdown 分析报告
    style_summary_markdown: NotRequired[str]  # markdown 风格摘要
    prompt_pack_markdown: NotRequired[str]  # markdown 风格母 Prompt 包
    analysis_meta: NotRequired[dict[str, Any]]  # 分析元数据统计信息


"""
ChunkMapState 是 Map 阶段（分块分析）每个并行任务的独立状态
每个 analyze_chunk 节点会收到一个独立的 ChunkMapState，包含该 chunk 的索引信息
这样设计避免了大状态在并行任务间的复制开销
"""


class ChunkMapState(TypedDict):
    job_id: str
    style_name: str
    model_name: str
    chunk_index: int  # 当前 chunk 的索引（0-based）
    chunk_count: int  # 总 chunk 数，用于在 Prompt 中告知 LLM 当前处理进度
    classification: InputClassification


# -----------------------------------------------------------------------------
# 结果定义层：流水线执行完成后的最终输出结构
# -----------------------------------------------------------------------------

"""
StyleAnalysisPipelineResult 是流水线的最终输出，不可变数据类
包含了分析过程产生的所有结构化产物，供上游调用方使用
"""


@dataclass(frozen=True)
class StyleAnalysisPipelineResult:
    analysis_meta: AnalysisMeta  # 分析元数据（字符数、切块数、模型信息等）
    analysis_report_markdown: str  # 完整 markdown 分析报告
    style_summary_markdown: str  # markdown 风格摘要
    prompt_pack_markdown: str  # markdown 风格母 Prompt 包


# 阶段切换回调函数类型定义：当流水线进入新阶段时会被调用，用于更新任务状态
StageCallback = Callable[[str | None], Awaitable[None]]


# -----------------------------------------------------------------------------
# 核心流水线实现：基于 LangGraph 的 MapReduce 风格分析引擎
# -----------------------------------------------------------------------------

"""
StyleAnalysisPipeline 是整个风格分析系统的核心执行引擎
采用 LangGraph 状态机 + MapReduce 架构，实现：
1. 可并行的分块深度分析
2. 可中断恢复的断点续跑（通过 Checkpointer）
3. Markdown 优先输出保证（通过 MarkdownLLMClient）
4. 阶段进度回调（用于实时展示分析进度）

完整执行流程：
prepare_input → [并行 N 个 analyze_chunk] → merge_chunks → build_report → build_summary → build_prompt_pack → persist_result
"""


class StyleAnalysisPipeline:
    def __init__(
        self,
        *,
        provider: ProviderConfig,  # LLM 提供商配置
        model_name: str,  # 使用的模型名称
        style_name: str,  # 风格名称
        source_filename: str,  # 原始文件名
        llm_client: MarkdownLLMClient | None = None,  # 可选注入的 LLM 客户端（便于测试）
        checkpointer: Any | None = None,  # 可选注入的 Checkpointer（用于持久化断点）
        stage_callback: StageCallback | None = None,  # 阶段切换回调
    ) -> None:
        self.provider = provider
        self.model_name = model_name
        self.style_name = style_name
        self.source_filename = source_filename

        # 初始化 Markdown LLM 客户端，所有 LLM 调用都通过此客户端输出纯文本 Markdown
        self.llm_client = llm_client or MarkdownLLMClient()
        self.chat_model = self.llm_client.build_model(
            provider=provider, model_name=model_name
        )

        # Checkpointer 用于 LangGraph 持久化状态，支持崩溃后断点续跑
        self.checkpointer = checkpointer or InMemorySaver()

        # 阶段回调：在流水线进入新阶段时触发，用于更新数据库中的任务阶段
        self.stage_callback = stage_callback

        # 存储服务：负责 chunk 文本和中间分析产物的读写
        self.storage_service = StyleAnalysisStorageService()

        # 构建并编译 LangGraph 状态图
        self.graph = self._build_graph()

    """
    运行整个分析流水线
    支持断点续跑：如果之前已经运行过且有 checkpoint，会从上次中断的节点继续执行
    """

    async def run(
        self,
        *,
        job_id: str,
        chunk_count: int,
        classification: InputClassification,
        max_concurrency: int,  # 分块分析阶段的最大并发数
    ) -> StyleAnalysisPipelineResult:
        # 构建初始状态，只包含运行流水线必须的最小信息
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

    """
    构建 LangGraph 状态图，定义整个流水线的执行流程
    采用 MapReduce 架构：先并行分析所有 chunk，再逐步聚合生成最终产物
    """

    def _build_graph(self):
        builder = StateGraph(StyleAnalysisState)

        # 注册所有节点
        builder.add_node("prepare_input", self._prepare_input)  # 输入准备与校验
        builder.add_node(
            "analyze_chunk", self._analyze_chunk
        )  # Map 阶段：单 chunk 分析（并行执行 N 次）
        builder.add_node(
            "merge_chunks", self._merge_chunks
        )  # Reduce 阶段：多 chunk 结果聚合
        builder.add_node("build_report", self._build_report)  # 生成完整分析报告
        builder.add_node("build_summary", self._build_summary)  # 生成风格摘要
        builder.add_node(
            "build_prompt_pack", self._build_prompt_pack
        )  # 生成风格母 Prompt 包
        builder.add_node("persist_result", self._persist_result)  # 组装最终元数据

        # 定义执行顺序与边
        builder.add_edge(START, "prepare_input")

        # 条件边：prepare_input 完成后，动态生成 N 个 analyze_chunk 并行任务
        builder.add_conditional_edges(
            "prepare_input", self._route_chunks, ["analyze_chunk"]
        )

        # 所有 analyze_chunk 完成后，进入 merge_chunks 阶段
        builder.add_edge("analyze_chunk", "merge_chunks")

        # 线性执行后续阶段
        builder.add_edge("merge_chunks", "build_report")
        builder.add_edge("build_report", "build_summary")
        builder.add_edge("build_summary", "build_prompt_pack")
        builder.add_edge("build_prompt_pack", "persist_result")
        builder.add_edge("persist_result", END)

        # 编译图，绑定 checkpointer 支持断点续跑
        return builder.compile(checkpointer=self.checkpointer)

    """
    输入准备节点：执行前置校验，设置初始阶段
    """

    async def _prepare_input(self, state: StyleAnalysisState) -> dict[str, Any]:
        if state["chunk_count"] < 1:
            raise RuntimeError("切片后没有可分析的有效文本")

        # 通知回调：进入分块分析阶段
        await self._set_stage(STYLE_ANALYSIS_JOB_STAGE_ANALYZING_CHUNKS)
        return {}

    """
    动态路由函数：为每个 chunk 生成一个独立的 analyze_chunk 任务
    这是 LangGraph 实现 Map 模式的标准方式，通过 Send 原语动态创建并行任务
    """

    def _route_chunks(self, state: StyleAnalysisState) -> list[Send]:
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

    """
    Map 阶段节点：分析单个文本 chunk
    此节点会被并行执行 N 次（N = chunk_count）
    每个节点独立读取 chunk、调用 LLM 分析、将结果写入存储
    不直接修改共享状态，避免并行写入冲突
    """

    async def _analyze_chunk(self, state: ChunkMapState) -> dict[str, Any]:
        # 从存储读取当前 chunk 的文本内容
        chunk = await self.storage_service.read_chunk_artifact(
            state["job_id"], state["chunk_index"]
        )

        # 构建针对该 chunk 的分析 Prompt
        prompt = build_chunk_analysis_prompt(
            chunk=chunk,
            chunk_index=state["chunk_index"],
            classification=state["classification"],
            chunk_count=state["chunk_count"],
        )

        # 调用 Markdown LLM 客户端，保证输出 Markdown 格式
        markdown = await self.llm_client.ainvoke_markdown(
            model=self.chat_model,
            prompt=prompt,
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

        # 不返回任何数据到共享状态，所有中间结果通过存储传递
        return {}

    """
    Reduce 阶段节点：将所有 chunk 的分析结果合并为单一的完整分析
    采用增量合并算法，每次最多合并 8 个 chunk 的结果，避免单次 Prompt 过长
    支持断点续跑：合并过程中的中间状态会被 Checkpointer 持久化
    """

    async def _merge_chunks(self, state: StyleAnalysisState) -> dict[str, Any]:
        await self._set_stage(STYLE_ANALYSIS_JOB_STAGE_AGGREGATING)

        merged: MergedAnalysis | None = None

        # 分批读取所有 chunk 的分析结果，每批最多 8 个
        async for batch in self.storage_service.read_chunk_analysis_batches(
            state["job_id"],
            batch_size=8,
        ):
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

            # 构建合并输入：当前批次的 chunk 分析 + 之前合并的结果
            merge_inputs = [item.model_dump(mode="json") for item in chunk_analyses]
            if merged is not None:
                merge_inputs.insert(0, merged.model_dump(mode="json"))

            # 调用 LLM 执行增量合并
            markdown = await self.llm_client.ainvoke_markdown(
                model=self.chat_model,
                prompt=build_merge_prompt(
                    chunk_analyses=merge_inputs,
                    classification=state["classification"],
                ),
            )
            merged = MergedAnalysis(
                classification=state["classification"],
                markdown=markdown,
            )

        if merged is None:
            raise RuntimeError("聚合阶段没有读到任何 chunk 分析结果")

        # 将合并结果写入共享状态，供后续阶段使用
        return {"merged_analysis_markdown": merged.markdown}

    """
    报告生成节点：基于合并后的分析结果，生成完整的多维度分析报告
    """

    async def _build_report(self, state: StyleAnalysisState) -> dict[str, Any]:
        await self._set_stage(STYLE_ANALYSIS_JOB_STAGE_REPORTING)

        report_markdown = await self.llm_client.ainvoke_markdown(
            model=self.chat_model,
            prompt=build_report_prompt(
                merged_analysis_markdown=state["merged_analysis_markdown"],
                classification=state["classification"],
            ),
        )

        return {"analysis_report_markdown": report_markdown}

    """
    风格摘要节点：从完整报告中提炼核心风格特征，生成精简的风格摘要
    """

    async def _build_summary(self, state: StyleAnalysisState) -> dict[str, Any]:
        await self._set_stage(STYLE_ANALYSIS_JOB_STAGE_SUMMARIZING)

        summary_markdown = await self.llm_client.ainvoke_markdown(
            model=self.chat_model,
            prompt=build_style_summary_prompt(
                report_markdown=state["analysis_report_markdown"],
                style_name=state["style_name"],
            ),
        )

        return {"style_summary_markdown": summary_markdown}

    """
    Prompt 包生成节点：基于分析报告和风格摘要，生成可直接调用的完整 Prompt 包
    包含系统提示词、风格指令、写作约束、输出格式规范等所有必要内容
    """

    async def _build_prompt_pack(self, state: StyleAnalysisState) -> dict[str, Any]:
        await self._set_stage(STYLE_ANALYSIS_JOB_STAGE_COMPOSING_PROMPT_PACK)

        prompt_pack_markdown = await self.llm_client.ainvoke_markdown(
            model=self.chat_model,
            prompt=build_prompt_pack_prompt(
                report_markdown=state["analysis_report_markdown"],
                style_summary_markdown=state["style_summary_markdown"],
            ),
        )

        return {"prompt_pack_markdown": prompt_pack_markdown}

    """
    结果持久化节点：组装分析元数据，准备最终输出
    此节点不涉及外部 IO，只是从状态中提取信息生成元数据对象
    """

    async def _persist_result(self, state: StyleAnalysisState) -> dict[str, Any]:
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

    """
    内部工具方法：触发阶段切换回调
    stage 为 None 表示流水线已完成
    """

    async def _set_stage(self, stage: str | None) -> None:
        if self.stage_callback is not None:
            await self.stage_callback(stage)
