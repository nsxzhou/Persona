from __future__ import annotations

import json
import operator
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated, Any, NotRequired, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.db.models import ProviderConfig
from app.schemas.style_analysis_jobs import (
    SECTION_TITLES,
    AnalysisMeta,
    AnalysisReport,
    ChunkAnalysis,
    MergedAnalysis,
    PromptPack,
    StyleSummary,
)
from app.services.style_analysis_llm import StructuredLLMClient

SHARED_ANALYSIS_RULES = """
你必须遵守以下规则：
1. 所有结论必须证据优先，不得编造不存在的设定、说话人或风格特征。
2. 输出必须使用中文简体，并严格匹配提供的结构化输出 schema。
3. 如果证据不足，必须明确使用低置信或弱判断，不得伪装成确定结论。
4. 关注文本类型、索引方式、噪声、批处理条件，并在后续分析中保持一致。
5. 3.1 到 3.12 的专题不能缺失，但某一节证据稀少时允许给出“当前样本中证据有限”的说明。
""".strip()


class StyleAnalysisState(TypedDict):
    job_id: NotRequired[str]
    style_name: str
    source_filename: str
    model_name: str
    cleaned_text: str
    chunks: list[str]
    classification: dict[str, Any]
    chunk_analyses: Annotated[list[dict[str, Any]], operator.add]
    merged_analysis: NotRequired[dict[str, Any]]
    analysis_report: NotRequired[dict[str, Any]]
    style_summary: NotRequired[dict[str, Any]]
    prompt_pack: NotRequired[dict[str, Any]]
    analysis_meta: NotRequired[dict[str, Any]]


class ChunkMapState(TypedDict):
    style_name: str
    model_name: str
    chunk: str
    chunk_index: int
    chunk_count: int
    classification: dict[str, Any]


@dataclass(frozen=True)
class StyleAnalysisPipelineResult:
    analysis_meta: AnalysisMeta
    analysis_report: AnalysisReport
    style_summary: StyleSummary
    prompt_pack: PromptPack


StageCallback = Callable[[str | None], Awaitable[None]]


class StyleAnalysisPipeline:
    def __init__(
        self,
        *,
        provider: ProviderConfig,
        model_name: str,
        style_name: str,
        source_filename: str,
        llm_client: StructuredLLMClient | None = None,
        checkpointer: Any | None = None,
        stage_callback: StageCallback | None = None,
    ) -> None:
        self.provider = provider
        self.model_name = model_name
        self.style_name = style_name
        self.source_filename = source_filename
        self.llm_client = llm_client or StructuredLLMClient()
        self.checkpointer = checkpointer or InMemorySaver()
        self.stage_callback = stage_callback
        self.graph = self._build_graph()

    async def run(
        self,
        *,
        thread_id: str,
        cleaned_text: str,
        chunks: list[str],
        classification: dict[str, Any],
        max_concurrency: int,
    ) -> StyleAnalysisPipelineResult:
        initial_state: StyleAnalysisState = {
            "style_name": self.style_name,
            "source_filename": self.source_filename,
            "model_name": self.model_name,
            "cleaned_text": cleaned_text,
            "chunks": chunks,
            "classification": classification,
            "chunk_analyses": [],
        }
        config = {
            "configurable": {"thread_id": thread_id},
            "max_concurrency": max_concurrency,
        }
        checkpoint_state = await self.graph.aget_state(config)
        graph_input = None if checkpoint_state.next else initial_state
        final_state = await self.graph.ainvoke(graph_input, config)
        await self._set_stage(None)
        return StyleAnalysisPipelineResult(
            analysis_meta=AnalysisMeta.model_validate(final_state["analysis_meta"]),
            analysis_report=AnalysisReport.model_validate(final_state["analysis_report"]),
            style_summary=StyleSummary.model_validate(final_state["style_summary"]),
            prompt_pack=PromptPack.model_validate(final_state["prompt_pack"]),
        )

    def _build_graph(self):
        builder = StateGraph(StyleAnalysisState)
        builder.add_node("prepare_input", self._prepare_input)
        builder.add_node("analyze_chunk", self._analyze_chunk)
        builder.add_node("merge_chunks", self._merge_chunks)
        builder.add_node("build_report", self._build_report)
        builder.add_node("build_summary", self._build_summary)
        builder.add_node("build_prompt_pack", self._build_prompt_pack)
        builder.add_node("persist_result", self._persist_result)
        builder.add_edge(START, "prepare_input")
        builder.add_conditional_edges("prepare_input", self._route_chunks, ["analyze_chunk"])
        builder.add_edge("analyze_chunk", "merge_chunks")
        builder.add_edge("merge_chunks", "build_report")
        builder.add_edge("build_report", "build_summary")
        builder.add_edge("build_summary", "build_prompt_pack")
        builder.add_edge("build_prompt_pack", "persist_result")
        builder.add_edge("persist_result", END)
        return builder.compile(checkpointer=self.checkpointer)

    async def _prepare_input(self, state: StyleAnalysisState) -> dict[str, Any]:
        if not state["cleaned_text"].strip():
            raise RuntimeError("清洗后没有可分析的有效文本")
        if not state["chunks"]:
            raise RuntimeError("切片后没有可分析的有效文本")
        await self._set_stage("analyzing_chunks")
        return {}

    def _route_chunks(self, state: StyleAnalysisState) -> list[Send]:
        chunk_count = len(state["chunks"])
        return [
            Send(
                "analyze_chunk",
                {
                    "style_name": state["style_name"],
                    "model_name": state["model_name"],
                    "chunk": chunk,
                    "chunk_index": index,
                    "chunk_count": chunk_count,
                    "classification": state["classification"],
                },
            )
            for index, chunk in enumerate(state["chunks"])
        ]

    async def _analyze_chunk(self, state: ChunkMapState) -> dict[str, Any]:
        prompt = self._build_chunk_analysis_prompt(
            chunk=state["chunk"],
            chunk_index=state["chunk_index"],
            classification=state["classification"],
            chunk_count=state["chunk_count"],
        )
        analysis = await self.llm_client.ainvoke_structured(
            provider=self.provider,
            model_name=self.model_name,
            schema=ChunkAnalysis,
            prompt=prompt,
        )
        return {"chunk_analyses": [analysis.model_dump(mode="json")]}

    async def _merge_chunks(self, state: StyleAnalysisState) -> dict[str, Any]:
        await self._set_stage("aggregating")
        chunk_analyses = sorted(
            (ChunkAnalysis.model_validate(item) for item in state["chunk_analyses"]),
            key=lambda item: item.chunk_index,
        )
        if len(chunk_analyses) == 1:
            merged = MergedAnalysis(
                classification=state["classification"],
                sections=chunk_analyses[0].sections,
            )
        else:
            prompt = self._build_merge_prompt(
                chunk_analyses=[item.model_dump(mode="json") for item in chunk_analyses],
                classification=state["classification"],
            )
            merged = await self.llm_client.ainvoke_structured(
                provider=self.provider,
                model_name=self.model_name,
                schema=MergedAnalysis,
                prompt=prompt,
            )
        return {"merged_analysis": merged.model_dump(mode="json")}

    async def _build_report(self, state: StyleAnalysisState) -> dict[str, Any]:
        await self._set_stage("reporting")
        report = await self.llm_client.ainvoke_structured(
            provider=self.provider,
            model_name=self.model_name,
            schema=AnalysisReport,
            prompt=self._build_report_prompt(
                merged_analysis=state["merged_analysis"],
                classification=state["classification"],
            ),
        )
        return {"analysis_report": report.model_dump(mode="json")}

    async def _build_summary(self, state: StyleAnalysisState) -> dict[str, Any]:
        await self._set_stage("summarizing")
        summary = await self.llm_client.ainvoke_structured(
            provider=self.provider,
            model_name=self.model_name,
            schema=StyleSummary,
            prompt=self._build_style_summary_prompt(
                report=state["analysis_report"],
                style_name=state["style_name"],
            ),
        )
        return {"style_summary": summary.model_dump(mode="json")}

    async def _build_prompt_pack(self, state: StyleAnalysisState) -> dict[str, Any]:
        await self._set_stage("composing_prompt_pack")
        prompt_pack = await self.llm_client.ainvoke_structured(
            provider=self.provider,
            model_name=self.model_name,
            schema=PromptPack,
            prompt=self._build_prompt_pack_prompt(
                report=state["analysis_report"],
                style_summary=state["style_summary"],
            ),
        )
        return {"prompt_pack": prompt_pack.model_dump(mode="json")}

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
            chunk_count=len(state["chunks"]),
        )
        return {"analysis_meta": analysis_meta.model_dump(mode="json")}

    async def _set_stage(self, stage: str | None) -> None:
        if self.stage_callback is not None:
            await self.stage_callback(stage)

    def _format_sections(self) -> str:
        return "\n".join(f"- {section} {title}" for section, title in SECTION_TITLES)

    def _build_chunk_analysis_prompt(
        self,
        *,
        chunk: str,
        chunk_index: int,
        classification: dict[str, Any],
        chunk_count: int,
    ) -> str:
        return (
            f"{SHARED_ANALYSIS_RULES}\n\n"
            "你正在执行分块分析阶段。请基于当前 chunk 的文本生成结构化输出。\n"
            "要求：\n"
            "1. sections 必须覆盖 3.1 到 3.12。\n"
            "2. 每节可以只有 1-3 条 finding；证据不足时仍保留该节并降低置信度。\n"
            "3. excerpt 必须来自样本文本，不得编造。\n"
            "4. confidence 只能是 high/medium/low。\n\n"
            f"输入判定：{json.dumps(classification, ensure_ascii=False)}\n"
            f"当前 chunk：{chunk_index + 1}/{chunk_count}\n"
            f"章节结构：\n{self._format_sections()}\n\n"
            f"样本文本：\n{chunk}"
        )

    def _build_merge_prompt(
        self,
        *,
        chunk_analyses: list[dict[str, Any]],
        classification: dict[str, Any],
    ) -> str:
        return (
            f"{SHARED_ANALYSIS_RULES}\n\n"
            "你正在执行全局聚合阶段。请把多个 chunk 的分析结果合并为统一结构化输出。\n"
            "要求：同义归并、重复证据去重、弱判断保留、多说话人差异不抹平。\n\n"
            f"输入判定：{json.dumps(classification, ensure_ascii=False)}\n"
            f"章节结构：\n{self._format_sections()}\n\n"
            f"待合并结果：\n{json.dumps(chunk_analyses, ensure_ascii=False)}"
        )

    def _build_report_prompt(
        self,
        *,
        merged_analysis: dict[str, Any],
        classification: dict[str, Any],
    ) -> str:
        return (
            f"{SHARED_ANALYSIS_RULES}\n\n"
            "你正在把聚合结果整理成最终分析报告。sections 必须覆盖 3.1 到 3.12。\n\n"
            f"输入判定：{json.dumps(classification, ensure_ascii=False)}\n"
            f"聚合结果：\n{json.dumps(merged_analysis, ensure_ascii=False)}"
        )

    def _build_style_summary_prompt(
        self,
        *,
        report: dict[str, Any],
        style_name: str,
    ) -> str:
        return (
            f"{SHARED_ANALYSIS_RULES}\n\n"
            "你正在从完整分析报告提炼可编辑风格摘要。"
            "不要引入报告中不存在的结论；尽量高密度、可用于后续生成。\n\n"
            f"风格名称：{style_name}\n"
            f"分析报告：\n{json.dumps(report, ensure_ascii=False)}"
        )

    def _build_prompt_pack_prompt(
        self,
        *,
        report: dict[str, Any],
        style_summary: dict[str, Any],
    ) -> str:
        return (
            "你是一位小说写作 prompt 编排器。"
            "请基于完整分析报告和当前风格摘要，生成一个全局可复用的风格母 prompt 包。"
            "不要绑定具体项目剧情，不要引入报告中没有的结论。\n\n"
            f"分析报告：\n{json.dumps(report, ensure_ascii=False)}\n\n"
            f"当前风格摘要：\n{json.dumps(style_summary, ensure_ascii=False)}"
        )
