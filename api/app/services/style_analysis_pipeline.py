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
    AnalysisMeta,
    AnalysisReport,
    ChunkAnalysis,
    MergedAnalysis,
    PromptPack,
    StyleSummary,
)
from app.services.style_analysis_llm import StructuredLLMClient
from app.services.style_analysis_text import InputClassification
from app.services.style_analysis_prompts import (
    build_chunk_analysis_prompt,
    build_merge_prompt,
    build_report_prompt,
    build_style_summary_prompt,
    build_prompt_pack_prompt,
)

class StyleAnalysisState(TypedDict):
    job_id: NotRequired[str]
    style_name: str
    source_filename: str
    model_name: str
    chunks: list[str]
    classification: InputClassification
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
    classification: InputClassification


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
        self.chat_model = self.llm_client.build_model(provider=provider, model_name=model_name)
        self.checkpointer = checkpointer or InMemorySaver()
        self.stage_callback = stage_callback
        self.graph = self._build_graph()

    async def run(
        self,
        *,
        thread_id: str,
        chunks: list[str],
        classification: InputClassification,
        max_concurrency: int,
    ) -> StyleAnalysisPipelineResult:
        initial_state: StyleAnalysisState = {
            "style_name": self.style_name,
            "source_filename": self.source_filename,
            "model_name": self.model_name,
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
        prompt = build_chunk_analysis_prompt(
            chunk=state["chunk"],
            chunk_index=state["chunk_index"],
            classification=state["classification"],
            chunk_count=state["chunk_count"],
        )
        analysis = await self.llm_client.ainvoke_structured(
            model=self.chat_model,
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
            prompt = build_merge_prompt(
                chunk_analyses=[item.model_dump(mode="json") for item in chunk_analyses],
                classification=state["classification"],
            )
            merged = await self.llm_client.ainvoke_structured(
                model=self.chat_model,
                schema=MergedAnalysis,
                prompt=prompt,
            )
        return {"merged_analysis": merged.model_dump(mode="json")}

    async def _build_report(self, state: StyleAnalysisState) -> dict[str, Any]:
        await self._set_stage("reporting")
        report = await self.llm_client.ainvoke_structured(
            model=self.chat_model,
            schema=AnalysisReport,
            prompt=build_report_prompt(
                merged_analysis=state["merged_analysis"],
                classification=state["classification"],
            ),
        )
        return {"analysis_report": report.model_dump(mode="json")}

    async def _build_summary(self, state: StyleAnalysisState) -> dict[str, Any]:
        await self._set_stage("summarizing")
        summary = await self.llm_client.ainvoke_structured(
            model=self.chat_model,
            schema=StyleSummary,
            prompt=build_style_summary_prompt(
                report=state["analysis_report"],
                style_name=state["style_name"],
            ),
        )
        return {"style_summary": summary.model_dump(mode="json")}

    async def _build_prompt_pack(self, state: StyleAnalysisState) -> dict[str, Any]:
        await self._set_stage("composing_prompt_pack")
        prompt_pack = await self.llm_client.ainvoke_structured(
            model=self.chat_model,
            schema=PromptPack,
            prompt=build_prompt_pack_prompt(
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
