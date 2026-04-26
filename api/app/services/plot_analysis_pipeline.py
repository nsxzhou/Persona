from __future__ import annotations
import asyncio
import json
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, NotRequired, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from pydantic import ValidationError

from app.db.models import ProviderConfig
from app.schemas.plot_analysis_jobs import (
    PlotAnalysisMeta,
    PlotChunkAnalysis,
    PlotChunkSketch,
    PlotMergedAnalysis,
    PLOT_ANALYSIS_JOB_STAGE_AGGREGATING,
    PLOT_ANALYSIS_JOB_STAGE_ANALYZING_FOCUS_CHUNKS,
    PLOT_ANALYSIS_JOB_STAGE_BUILDING_SKELETON,
    PLOT_ANALYSIS_JOB_STAGE_POSTPROCESSING,
    PLOT_ANALYSIS_JOB_STAGE_REPORTING,
    PLOT_ANALYSIS_JOB_STAGE_SELECTING_FOCUS_CHUNKS,
)
from app.services.style_analysis_llm import MarkdownLLMClient
from app.services.prompt_injection_policy import PromptInjectionTask
from app.services.plot_analysis_prompts import (
    build_chunk_analysis_prompt,
    build_merge_prompt,
    build_report_prompt,
    build_sketch_prompt,
    build_skeleton_group_reduce_prompt,
    build_skeleton_reduce_prompt,
    build_story_engine_prompt,
)
from app.services.plot_analysis_storage import PlotAnalysisStorageService
from app.services.style_analysis_text import InputClassification

logger = logging.getLogger(__name__)


# Hierarchical skeleton reduce triggers when the rough token estimate
# of sketches exceeds this threshold. Tuned for a ~100K context budget
# leaving headroom for prompt scaffolding. Module-level so tests can
# monkeypatch it without synthesising gigantic sketch payloads.
SKELETON_HIERARCHICAL_TOKEN_THRESHOLD = 80_000

# Group size for the hierarchical group-reduce step. Also monkeypatch-able.
SKELETON_GROUP_SIZE = 40

_PLOT_WRITING_GUIDE_SECTION_HEADERS = (
    "# Plot Writing Guide",
    "## Core Plot Formula",
    "## Chapter Progression Loop",
    "## Scene Construction Rules",
    "## Setup and Payoff Rules",
    "## Payoff and Tension Rhythm",
    "## Side Plot Usage",
    "## Hook Recipes",
    "## Anti-Drift Rules",
)


class PlotAnalysisPauseRequested(Exception):
    pass


class PlotAnalysisState(TypedDict):
    job_id: str
    plot_name: str
    source_filename: str
    model_name: str
    chunk_count: int
    classification: InputClassification

    focus_chunk_indexes: NotRequired[list[int]]
    plot_skeleton_markdown: NotRequired[str]
    merged_analysis_markdown: NotRequired[str]
    analysis_report_markdown: NotRequired[str]
    story_engine_markdown: NotRequired[str]
    analysis_meta: NotRequired[dict[str, Any]]


class SketchMapState(TypedDict):
    job_id: str
    plot_name: str
    model_name: str
    chunk_index: int
    chunk_count: int
    classification: InputClassification


class ChunkMapState(TypedDict):
    job_id: str
    plot_name: str
    model_name: str
    chunk_index: int
    chunk_count: int
    classification: InputClassification


@dataclass(frozen=True)
class PlotAnalysisPipelineResult:
    analysis_meta: PlotAnalysisMeta
    analysis_report_markdown: str
    story_engine_markdown: str
    plot_skeleton_markdown: str


StageCallback = Callable[[str | None], Awaitable[None]]


class PlotAnalysisPipeline:
    def __init__(
        self,
        *,
        provider: ProviderConfig,
        model_name: str,
        plot_name: str,
        source_filename: str,
        llm_client: MarkdownLLMClient | None = None,
        chat_model: Any | None = None,
        checkpointer: Any | None = None,
        storage_service: PlotAnalysisStorageService | None = None,
        stage_callback: StageCallback | None = None,
        should_pause: Callable[[], bool] | None = None,
    ) -> None:
        self.provider = provider
        self.model_name = model_name
        self.plot_name = plot_name
        self.source_filename = source_filename

        self.llm_client = llm_client or MarkdownLLMClient()
        self.chat_model = chat_model or self.llm_client.build_model(
            provider=provider, model_name=model_name
        )

        if checkpointer is None:
            logger.warning(
                "PlotAnalysisPipeline falling back to in-memory checkpointer; "
                "resume across process restarts will be lost.",
            )
            self.checkpointer = InMemorySaver()
        else:
            self.checkpointer = checkpointer

        self.stage_callback = stage_callback
        self.should_pause = should_pause
        self.storage_service = storage_service or PlotAnalysisStorageService()
        self._plot_skeleton_cache: str | None = None
        self.graph = self._build_graph()

    @staticmethod
    def _normalize_story_engine_markdown(markdown: str) -> str:
        stripped = markdown.strip()
        if not stripped:
            return stripped

        first_header = _PLOT_WRITING_GUIDE_SECTION_HEADERS[0]
        start = stripped.find(first_header)
        if start >= 0:
            stripped = stripped[start:]

        matches = list(
            re.finditer(r"^(#|##) [^\n]+", stripped, flags=re.MULTILINE)
        )
        if not matches:
            return stripped

        sections: list[str] = []
        for index, match in enumerate(matches):
            header = match.group(0).strip()
            if header not in _PLOT_WRITING_GUIDE_SECTION_HEADERS:
                continue
            section_end = matches[index + 1].start() if index + 1 < len(matches) else len(stripped)
            section_body = stripped[match.start():section_end].strip()
            sections.append(section_body)

        return "\n\n".join(sections).strip()

    async def run(
        self,
        *,
        job_id: str,
        chunk_count: int,
        classification: InputClassification,
        max_concurrency: int,
    ) -> PlotAnalysisPipelineResult:
        initial_state: PlotAnalysisState = {
            "job_id": job_id,
            "plot_name": self.plot_name,
            "source_filename": self.source_filename,
            "model_name": self.model_name,
            "chunk_count": chunk_count,
            "classification": classification,
        }

        config = {
            "configurable": {"thread_id": job_id},
            "max_concurrency": max_concurrency,
        }

        checkpoint_state = await self.graph.aget_state(config)
        graph_input = None if checkpoint_state.next else initial_state
        final_state = await self.graph.ainvoke(graph_input, config)
        await self._clear_stage_on_completion()

        return PlotAnalysisPipelineResult(
            analysis_meta=PlotAnalysisMeta.model_validate(final_state["analysis_meta"]),
            analysis_report_markdown=str(final_state["analysis_report_markdown"]),
            story_engine_markdown=str(final_state["story_engine_markdown"]),
            plot_skeleton_markdown=str(final_state["plot_skeleton_markdown"]),
        )

    def _build_graph(self):
        builder = StateGraph(PlotAnalysisState)

        builder.add_node("prepare_input", self._prepare_input)
        builder.add_node("sketch_chunk", self._sketch_chunk)
        builder.add_node("build_skeleton", self._build_skeleton)
        builder.add_node("build_report", self._build_report)
        builder.add_node("build_story_engine", self._build_story_engine)
        builder.add_node("persist_result", self._persist_result)

        builder.add_edge(START, "prepare_input")
        builder.add_conditional_edges("prepare_input", self._route_sketches, ["sketch_chunk"])
        builder.add_edge("sketch_chunk", "build_skeleton")
        builder.add_edge("build_skeleton", "build_report")
        builder.add_edge("build_report", "build_story_engine")
        builder.add_edge("build_story_engine", "persist_result")
        builder.add_edge("persist_result", END)

        return builder.compile(checkpointer=self.checkpointer)

    async def _prepare_input(self, state: PlotAnalysisState) -> dict[str, Any]:
        self._raise_if_paused()
        if state["chunk_count"] < 1:
            raise RuntimeError("切片后没有可分析的有效文本")

        await self._set_stage(PLOT_ANALYSIS_JOB_STAGE_BUILDING_SKELETON)
        await self.storage_service.append_job_log(
            state["job_id"],
            f"[System] 开始分析任务，共分为 {state['chunk_count']} 个文本分块进行并发处理..."
        )
        return {}

    def _route_sketches(self, state: PlotAnalysisState) -> list[Send]:
        self._raise_if_paused()
        max_chunks = 1000
        if state["chunk_count"] > max_chunks:
            raise ValueError(f"切片数量超过上限 ({max_chunks})，请更换较小样本或增加切分阈值。")
        return [
            Send(
                "sketch_chunk",
                {
                    "job_id": state["job_id"],
                    "plot_name": state["plot_name"],
                    "model_name": state["model_name"],
                    "chunk_index": index,
                    "chunk_count": state["chunk_count"],
                    "classification": state["classification"],
                },
            )
            for index in range(state["chunk_count"])
        ]

    async def _sketch_chunk(self, state: SketchMapState) -> dict[str, Any]:
        self._raise_if_paused()
        await self.storage_service.append_job_log(
            state["job_id"],
            f"[LLM] 正在并行生成 sketch {state['chunk_index'] + 1}/{state['chunk_count']} ..."
        )
        if self.storage_service.sketch_artifact_exists(state["job_id"], state["chunk_index"]):
            return {}
        chunk_context = await self.storage_service.read_chunk_with_overlap_context(
            state["job_id"],
            state["chunk_index"],
        )

        prompt = build_sketch_prompt(
            chunk=chunk_context.primary_text,
            chunk_index=state["chunk_index"],
            chunk_count=state["chunk_count"],
            classification=state["classification"],
            overlap_before=chunk_context.overlap_before,
            overlap_after=chunk_context.overlap_after,
        )

        raw = await self.llm_client.ainvoke_markdown(
            model=self.chat_model,
            prompt=prompt,
            provider=self.provider,
            model_name=self.model_name,
            injection_task=PromptInjectionTask.PLOT_ANALYSIS_SKETCH,
        )

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            await self.storage_service.append_job_log(
                state["job_id"],
                f"[Error] sketch {state['chunk_index']+1}/{state['chunk_count']} 返回非法 JSON: {exc}"
            )
            raise RuntimeError(
                f"Sketch chunk {state['chunk_index']} produced invalid JSON"
            ) from exc

        # Defensive: enforce chunk_index/chunk_count from the state; LLMs sometimes drift.
        data["chunk_index"] = state["chunk_index"]
        data["chunk_count"] = state["chunk_count"]

        try:
            sketch = PlotChunkSketch.model_validate(data)
        except ValidationError as exc:
            await self.storage_service.append_job_log(
                state["job_id"],
                f"[LLM] sketch {state['chunk_index']+1}/{state['chunk_count']} 形状校验失败: {exc}"
            )
            raise RuntimeError(
                f"Sketch chunk {state['chunk_index']} shape invalid"
            ) from exc
        await self.storage_service.write_sketch_artifact(
            state["job_id"],
            state["chunk_index"],
            sketch.model_dump(mode="json"),
        )
        await self.storage_service.append_job_log(
            state["job_id"],
            f"[LLM] sketch {state['chunk_index']+1}/{state['chunk_count']} 完成"
        )
        return {}

    async def _build_skeleton(self, state: PlotAnalysisState) -> dict[str, Any]:
        self._raise_if_paused()
        await self._set_stage(PLOT_ANALYSIS_JOB_STAGE_BUILDING_SKELETON)
        await self.storage_service.append_job_log(
            state["job_id"],
            "[System] 正在构建全书骨架 ..."
        )

        if self.storage_service.stage_markdown_artifact_exists(state["job_id"], name="plot-skeleton"):
            markdown = await self.storage_service.read_stage_markdown_artifact(
                state["job_id"], name="plot-skeleton"
            )
            return {"plot_skeleton_markdown": markdown}

        sketches = await self.storage_service.read_all_sketches(state["job_id"])
        if not sketches:
            raise RuntimeError("骨架构建阶段没有读到任何 sketch 结果")

        # Hierarchical fallback heuristic: rough tokens ≈ sum(len(json.dumps(s))) / 3.
        rough_tokens = sum(len(json.dumps(s, ensure_ascii=False)) for s in sketches) // 3
        if rough_tokens > SKELETON_HIERARCHICAL_TOKEN_THRESHOLD:
            await self.storage_service.append_job_log(
                state["job_id"],
                f"[System] sketch 规模过大 (~{rough_tokens} tokens)，启用分层归约 ..."
            )
            markdown = await self._build_skeleton_hierarchical(
                state=state,
                sketches=sketches,
            )
        else:
            markdown = await self.llm_client.ainvoke_markdown(
                model=self.chat_model,
                prompt=build_skeleton_reduce_prompt(
                    sketches=sketches,
                    classification=state["classification"],
                    chunk_count=state["chunk_count"],
                ),
                provider=self.provider,
                model_name=self.model_name,
                injection_task=PromptInjectionTask.PLOT_ANALYSIS_SKELETON,
            )

        await self.storage_service.write_stage_markdown_artifact(
            state["job_id"], name="plot-skeleton", markdown=markdown
        )
        await self.storage_service.append_job_log(state["job_id"], "[System] 骨架构建完成")
        return {"plot_skeleton_markdown": markdown}

    async def _build_skeleton_hierarchical(
        self,
        *,
        state: PlotAnalysisState,
        sketches: list[dict[str, Any]],
    ) -> str:
        # Group sketches into batches, reduce each into a sub-skeleton, then reduce all sub-skeletons.
        group_size = SKELETON_GROUP_SIZE
        groups: list[list[dict[str, Any]]] = [
            sketches[i:i + group_size] for i in range(0, len(sketches), group_size)
        ]
        if len(groups) == 1:
            # Only one group — degenerate hierarchy. Fall back to the single-call reduce.
            return await self.llm_client.ainvoke_markdown(
                model=self.chat_model,
                prompt=build_skeleton_reduce_prompt(
                    sketches=sketches,
                    classification=state["classification"],
                    chunk_count=state["chunk_count"],
                ),
                provider=self.provider,
                model_name=self.model_name,
                injection_task=PromptInjectionTask.PLOT_ANALYSIS_SKELETON,
            )
        sub_skeletons: list[str] = []
        async def process_group(idx: int, group: list[dict[str, Any]]) -> str:
            self._raise_if_paused()
            await self.storage_service.append_job_log(
                state["job_id"],
                f"[LLM] 分层归约 group {idx+1}/{len(groups)} (含 {len(group)} 个 sketch)"
            )
            return await self.llm_client.ainvoke_markdown(
                model=self.chat_model,
                prompt=build_skeleton_group_reduce_prompt(
                    group_sketches=group,
                    group_index=idx,
                    group_count=len(groups),
                    classification=state["classification"],
                ),
                provider=self.provider,
                model_name=self.model_name,
                injection_task=PromptInjectionTask.PLOT_ANALYSIS_SKELETON_GROUP,
            )

        tasks = [process_group(idx, group) for idx, group in enumerate(groups)]
        sub_skeletons = list(await asyncio.gather(*tasks))

        # Final reduce: wrap sub-skeleton markdowns so they can re-enter the reduce prompt;
        # build_skeleton_reduce_prompt explicitly tolerates either sketch-dict or sub-skeleton-dict.
        wrapped = [
            {"sub_skeleton_index": i, "markdown": md} for i, md in enumerate(sub_skeletons)
        ]
        final_md = await self.llm_client.ainvoke_markdown(
            model=self.chat_model,
            prompt=build_skeleton_reduce_prompt(
                sketches=wrapped,
                classification=state["classification"],
                chunk_count=state["chunk_count"],
            ),
            provider=self.provider,
            model_name=self.model_name,
            injection_task=PromptInjectionTask.PLOT_ANALYSIS_SKELETON,
        )
        return final_md

    def _route_chunks(self, state: PlotAnalysisState) -> list[Send]:
        self._raise_if_paused()
        max_chunks = 1000
        if state["chunk_count"] > max_chunks:
            raise ValueError(f"切片数量超过上限 ({max_chunks})，请更换较小样本或增加切分阈值。")
        skeleton = state.get("plot_skeleton_markdown")
        if not skeleton:
            raise RuntimeError(
                "plot_skeleton_markdown is required before routing chunks; "
                "build_skeleton must run first."
            )
        self._plot_skeleton_cache = skeleton
        focus_chunk_indexes = set(state.get("focus_chunk_indexes", range(state["chunk_count"])))
        return [
            Send(
                "analyze_chunk",
                {
                    "job_id": state["job_id"],
                    "plot_name": state["plot_name"],
                    "model_name": state["model_name"],
                    "chunk_index": index,
                    "chunk_count": state["chunk_count"],
                    "classification": state["classification"],
                },
            )
            for index in range(state["chunk_count"])
            if index in focus_chunk_indexes
        ]

    async def _select_focus_chunks(self, state: PlotAnalysisState) -> dict[str, Any]:
        self._raise_if_paused()
        await self._set_stage(PLOT_ANALYSIS_JOB_STAGE_SELECTING_FOCUS_CHUNKS)
        sketches = await self.storage_service.read_all_sketches(state["job_id"])
        focus_chunk_indexes = self._select_focus_chunk_indexes(
            chunk_count=state["chunk_count"],
            sketches=sketches,
            plot_skeleton_markdown=state.get("plot_skeleton_markdown"),
        )
        await self.storage_service.append_job_log(
            state["job_id"],
            f"[System] 已选择 {len(focus_chunk_indexes)}/{state['chunk_count']} 个重点分块进行深分析..."
        )
        return {"focus_chunk_indexes": focus_chunk_indexes}

    def _select_focus_chunk_indexes(
        self,
        *,
        chunk_count: int,
        sketches: list[dict[str, Any]],
        plot_skeleton_markdown: str | None,
    ) -> list[int]:
        if chunk_count <= 3:
            return list(range(chunk_count))

        selected: set[int] = {0, max(0, chunk_count - 1)}

        for sketch in sketches:
            index = sketch.get("chunk_index")
            if not isinstance(index, int):
                continue
            if sketch.get("payoff_points") or sketch.get("tension_points") or sketch.get("hooks"):
                selected.add(index)

        if plot_skeleton_markdown:
            for match in re.finditer(r"chunk\s*(\d+)(?:\s*-\s*(\d+))?|@chunk(\d+)", plot_skeleton_markdown):
                start = match.group(1)
                end = match.group(2)
                single = match.group(3)
                if single is not None:
                    selected.add(int(single))
                    continue
                if start is None:
                    continue
                start_index = int(start)
                end_index = int(end) if end is not None else start_index
                selected.add(start_index)
                selected.add(end_index)

        if chunk_count > 4:
            selected.add(chunk_count // 2)

        clamped = sorted(index for index in selected if 0 <= index < chunk_count)
        return clamped or list(range(chunk_count))

    async def _get_plot_skeleton_markdown(self, job_id: str) -> str:
        if self._plot_skeleton_cache is None:
            self._plot_skeleton_cache = await self.storage_service.read_stage_markdown_artifact(
                job_id,
                name="plot-skeleton",
            )
        return self._plot_skeleton_cache

    async def _analyze_chunk(self, state: ChunkMapState) -> dict[str, Any]:
        self._raise_if_paused()
        await self._set_stage(PLOT_ANALYSIS_JOB_STAGE_ANALYZING_FOCUS_CHUNKS)
        await self.storage_service.append_job_log(
            state["job_id"],
            f"[LLM] 正在并行处理 分块 {state['chunk_index'] + 1}/{state['chunk_count']} ..."
        )
        if self.storage_service.chunk_analysis_artifact_exists(state["job_id"], state["chunk_index"]):
            return {}
        chunk_context = await self.storage_service.read_chunk_with_overlap_context(
            state["job_id"],
            state["chunk_index"],
        )
        plot_skeleton_markdown = await self._get_plot_skeleton_markdown(state["job_id"])

        prompt = build_chunk_analysis_prompt(
            chunk=chunk_context.primary_text,
            chunk_index=state["chunk_index"],
            classification=state["classification"],
            chunk_count=state["chunk_count"],
            plot_skeleton=plot_skeleton_markdown,
            overlap_before=chunk_context.overlap_before,
            overlap_after=chunk_context.overlap_after,
        )

        markdown = await self.llm_client.ainvoke_markdown(
            model=self.chat_model,
            prompt=prompt,
            provider=self.provider,
            model_name=self.model_name,
            injection_task=PromptInjectionTask.PLOT_ANALYSIS_CHUNK,
        )

        await self.storage_service.write_chunk_analysis_artifact(
            state["job_id"],
            state["chunk_index"],
            PlotChunkAnalysis(
                chunk_index=state["chunk_index"],
                chunk_count=state["chunk_count"],
                markdown=markdown,
            ).model_dump(mode="json"),
        )

        await self.storage_service.append_job_log(
            state["job_id"],
            f"[LLM] 分块 {state['chunk_index'] + 1}/{state['chunk_count']} 分析完成"
        )
        return {}

    async def _merge_chunks(self, state: PlotAnalysisState) -> dict[str, Any]:
        self._raise_if_paused()
        await self._set_stage(PLOT_ANALYSIS_JOB_STAGE_AGGREGATING)
        await self.storage_service.append_job_log(
            state["job_id"],
            f"[LangGraph] 正在执行 Reduce 聚合操作 (合并 {state['chunk_count']} 个分块的结果)..."
        )

        if self.storage_service.stage_markdown_artifact_exists(state["job_id"], name="merged-analysis"):
            markdown = await self.storage_service.read_stage_markdown_artifact(state["job_id"], name="merged-analysis")
            return {"merged_analysis_markdown": markdown}

        merged: PlotMergedAnalysis | None = None
        batch_index = 0
        async for batch in self.storage_service.read_chunk_analysis_batches(state["job_id"], batch_size=20):
            self._raise_if_paused()
            batch_index += 1
            chunk_analyses = sorted(
                (PlotChunkAnalysis.model_validate(item) for item in batch),
                key=lambda item: item.chunk_index,
            )

            if merged is None and len(chunk_analyses) == 1:
                merged = PlotMergedAnalysis(
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

            merge_inputs = [item.model_dump(mode="json") for item in chunk_analyses]
            if merged is not None:
                merge_inputs.insert(0, merged.model_dump(mode="json"))

            markdown = await self.llm_client.ainvoke_markdown(
                model=self.chat_model,
                prompt=build_merge_prompt(
                    chunk_analyses=merge_inputs,
                    classification=state["classification"],
                    plot_skeleton=state.get("plot_skeleton_markdown"),
                ),
                provider=self.provider,
                model_name=self.model_name,
                injection_task=PromptInjectionTask.PLOT_ANALYSIS_MERGE,
            )
            merged = PlotMergedAnalysis(
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
        return {"merged_analysis_markdown": merged.markdown}

    async def _build_report(self, state: PlotAnalysisState) -> dict[str, Any]:
        self._raise_if_paused()
        await self._set_stage(PLOT_ANALYSIS_JOB_STAGE_REPORTING)
        await self.storage_service.append_job_log(state["job_id"], "[System] 正在生成最终 Markdown 报告...")

        if self.storage_service.stage_markdown_artifact_exists(state["job_id"], name="analysis-report"):
            markdown = await self.storage_service.read_stage_markdown_artifact(state["job_id"], name="analysis-report")
            return {"analysis_report_markdown": markdown}

        report_markdown = await self.llm_client.ainvoke_markdown(
            model=self.chat_model,
            prompt=build_report_prompt(
                merged_analysis_markdown=state["plot_skeleton_markdown"],
                classification=state["classification"],
                plot_skeleton=state.get("plot_skeleton_markdown"),
            ),
            provider=self.provider,
            model_name=self.model_name,
            injection_task=PromptInjectionTask.PLOT_ANALYSIS_REPORT,
        )

        await self.storage_service.write_stage_markdown_artifact(
            state["job_id"], name="analysis-report", markdown=report_markdown
        )
        return {"analysis_report_markdown": report_markdown}

    async def _build_story_engine(self, state: PlotAnalysisState) -> dict[str, Any]:
        self._raise_if_paused()
        await self._set_stage(PLOT_ANALYSIS_JOB_STAGE_POSTPROCESSING)
        await self.storage_service.append_job_log(state["job_id"], "[System] 正在生成 Plot Writing Guide...")

        if self.storage_service.stage_markdown_artifact_exists(state["job_id"], name="story-engine"):
            markdown = await self.storage_service.read_stage_markdown_artifact(state["job_id"], name="story-engine")
            return {
                "story_engine_markdown": markdown,
            }

        story_engine_markdown = await self.llm_client.ainvoke_markdown(
            model=self.chat_model,
            prompt=build_story_engine_prompt(
                report_markdown=state["analysis_report_markdown"],
                plot_name=state["plot_name"],
            ),
            provider=self.provider,
            model_name=self.model_name,
            injection_task=PromptInjectionTask.PLOT_ANALYSIS_STORY_ENGINE,
        )
        story_engine_markdown = self._normalize_story_engine_markdown(story_engine_markdown)

        await self.storage_service.write_stage_markdown_artifact(
            state["job_id"], name="story-engine", markdown=story_engine_markdown
        )
        return {
            "story_engine_markdown": story_engine_markdown,
        }

    async def _persist_result(self, state: PlotAnalysisState) -> dict[str, Any]:
        self._raise_if_paused()
        await self.storage_service.append_job_log(state["job_id"], "[System] 分析任务全部完成！")
        analysis_meta = PlotAnalysisMeta(
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
        self._raise_if_paused()
        if self.stage_callback is not None:
            try:
                await self.stage_callback(stage)
            except Exception:
                logger.exception("Stage callback failed, continuing pipeline")

    async def _clear_stage_on_completion(self) -> None:
        if self.stage_callback is not None:
            await self.stage_callback(None)

    def _raise_if_paused(self) -> None:
        if self.should_pause is not None and self.should_pause():
            raise PlotAnalysisPauseRequested()
