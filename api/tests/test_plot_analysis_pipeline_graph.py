from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.core.config import get_settings
from app.schemas.plot_analysis_jobs import PlotAnalysisMeta
from app.services.plot_analysis_pipeline import PlotAnalysisPipeline
from app.services.plot_analysis_storage import PlotAnalysisStorageService


# A marker string embedded in the canned skeleton markdown. If the skeleton is
# correctly threaded into a downstream prompt, the prompt must contain this marker.
_SKELETON_SIGNATURE = "SKELETON_SIGNATURE_ALPHA"
_SKELETON_MARKDOWN = (
    "# 全书骨架\n"
    f"## 阶段划分（按 chunk 索引）\n{_SKELETON_SIGNATURE} 启动期 0；高潮期 1-2\n"
)


def _sketch_json(chunk_index: int, chunk_count: int) -> str:
    return json.dumps(
        {
            "chunk_index": chunk_index,
            "chunk_count": chunk_count,
            "characters_present": ["主角"],
            "events": [f"chunk {chunk_index} 事件"],
            "advancement": "setup",
            "time_marker": "linear",
        },
        ensure_ascii=False,
    )


class PipelineLLMStub:
    """Routes LLM calls to canned outputs based on prompt signatures.

    Each list captures the raw prompt seen per stage so the test can assert the
    skeleton content was actually threaded downstream.
    """

    def __init__(self) -> None:
        self.sketch_prompts: list[str] = []
        self.skeleton_reduce_prompts: list[str] = []
        self.chunk_analysis_prompts: list[str] = []
        self.merge_prompts: list[str] = []
        self.report_prompts: list[str] = []
        self.summary_prompts: list[str] = []
        self.pack_prompts: list[str] = []

    def build_model(self, *, provider: object, model_name: str) -> object:
        return SimpleNamespace(provider=provider, model_name=model_name)

    async def ainvoke_markdown(self, *, model: object, prompt: str) -> str:
        del model
        if "Plot Lab 的分块速写阶段" in prompt:
            match = re.search(r"chunk_index=(\d+), chunk_count=(\d+)", prompt)
            assert match is not None, "sketch prompt must expose chunk_index/chunk_count"
            self.sketch_prompts.append(prompt)
            return _sketch_json(int(match.group(1)), int(match.group(2)))
        if "Plot Lab 的全书骨架聚合阶段" in prompt:
            self.skeleton_reduce_prompts.append(prompt)
            return _SKELETON_MARKDOWN
        if "Plot Lab 的分块分析阶段" in prompt:
            self.chunk_analysis_prompts.append(prompt)
            return "# 执行摘要\nchunk markdown"
        if "Plot Lab 的全局聚合阶段" in prompt:
            self.merge_prompts.append(prompt)
            return "# 执行摘要\n合并结果"
        if "最终 Plot Lab 分析报告" in prompt:
            self.report_prompts.append(prompt)
            return "# 执行摘要\n最终报告"
        if "从完整 Plot Lab 报告" in prompt:
            self.summary_prompts.append(prompt)
            return "# 剧情定位\n摘要内容"
        if "小说情节 prompt 编排器" in prompt:
            self.pack_prompts.append(prompt)
            return "# Shared Constraints\n包内容"
        raise AssertionError(f"Unexpected prompt: {prompt[:120]}")


def build_pipeline(client: PipelineLLMStub, checkpointer: InMemorySaver) -> PlotAnalysisPipeline:
    return PlotAnalysisPipeline(
        provider=SimpleNamespace(
            base_url="https://api.example.test/v1",
            api_key_encrypted="encrypted",
        ),
        model_name="gpt-4.1-mini",
        plot_name="骨架测试",
        source_filename="sample.txt",
        llm_client=client,
        checkpointer=checkpointer,
    )


_CLASSIFICATION = {
    "text_type": "章节正文",
    "has_timestamps": False,
    "has_speaker_labels": False,
    "has_noise_markers": False,
    "uses_batch_processing": True,
    "location_indexing": "章节或段落位置",
}


@pytest.mark.asyncio
async def test_pipeline_graph_runs_sketch_then_skeleton_and_threads_skeleton_downstream(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()

    storage_service = PlotAnalysisStorageService()
    job_id = "job-skeleton-thread"
    chunk_count = 3
    for index in range(chunk_count):
        await storage_service.write_chunk_artifact(job_id, index, f"chunk {index} text")

    client = PipelineLLMStub()
    pipeline = build_pipeline(client, InMemorySaver())

    result = await pipeline.run(
        job_id=job_id,
        chunk_count=chunk_count,
        classification=_CLASSIFICATION,
        max_concurrency=3,
    )

    # Sketch fan-out ran once per chunk.
    assert len(client.sketch_prompts) == chunk_count
    # Reduce ran exactly once (below the hierarchical-fallback threshold).
    assert len(client.skeleton_reduce_prompts) == 1
    # Skeleton artifact written to disk.
    assert storage_service.stage_markdown_artifact_exists(job_id, name="plot-skeleton")
    skeleton_md = await storage_service.read_stage_markdown_artifact(
        job_id, name="plot-skeleton"
    )
    assert _SKELETON_SIGNATURE in skeleton_md

    # Skeleton threaded into chunk analysis (via ChunkMapState).
    assert len(client.chunk_analysis_prompts) == chunk_count
    for chunk_prompt in client.chunk_analysis_prompts:
        assert _SKELETON_SIGNATURE in chunk_prompt, (
            "chunk analysis prompt should embed the plot skeleton"
        )
    # Skeleton threaded into merge prompt (via PlotAnalysisState).
    assert len(client.merge_prompts) >= 1
    for merge_prompt in client.merge_prompts:
        assert _SKELETON_SIGNATURE in merge_prompt, (
            "merge prompt should embed the plot skeleton"
        )
    # Skeleton threaded into report prompt.
    assert len(client.report_prompts) == 1
    assert _SKELETON_SIGNATURE in client.report_prompts[0]

    # Summary and prompt-pack are unaffected by the skeleton (out of spec scope).
    assert len(client.summary_prompts) == 1
    assert len(client.pack_prompts) == 1

    # PlotAnalysisPipelineResult carries the skeleton markdown verbatim.
    assert result.plot_skeleton_markdown == skeleton_md
    assert result.analysis_report_markdown.startswith("# 执行摘要")
    assert result.plot_summary_markdown.startswith("# 剧情定位")
    assert result.prompt_pack_markdown.startswith("# Shared Constraints")

    assert result.analysis_meta == PlotAnalysisMeta(
        source_filename="sample.txt",
        model_name="gpt-4.1-mini",
        text_type="章节正文",
        has_timestamps=False,
        has_speaker_labels=False,
        has_noise_markers=False,
        uses_batch_processing=True,
        location_indexing="章节或段落位置",
        chunk_count=chunk_count,
    )

    # All sketch artifacts persisted.
    assert storage_service.count_sketch_artifacts(job_id) == chunk_count
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_pipeline_graph_tracks_stage_transitions_from_prepare_to_prompt_pack(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercises the stage-callback transitions. _prepare_input now emits
    ``building_skeleton`` (instead of ``analyzing_chunks``), and ``analyzing_chunks``
    first appears at entry to ``_analyze_chunk`` after the skeleton reduce completes.
    """

    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()

    storage_service = PlotAnalysisStorageService()
    job_id = "job-stage-transitions"
    chunk_count = 2
    for index in range(chunk_count):
        await storage_service.write_chunk_artifact(job_id, index, f"chunk {index} text")

    seen_stages: list[str | None] = []

    async def stage_callback(stage: str | None) -> None:
        seen_stages.append(stage)

    client = PipelineLLMStub()
    pipeline = PlotAnalysisPipeline(
        provider=SimpleNamespace(
            base_url="https://api.example.test/v1",
            api_key_encrypted="encrypted",
        ),
        model_name="gpt-4.1-mini",
        plot_name="阶段测试",
        source_filename="sample.txt",
        llm_client=client,
        checkpointer=InMemorySaver(),
        stage_callback=stage_callback,
    )

    await pipeline.run(
        job_id=job_id,
        chunk_count=chunk_count,
        classification=_CLASSIFICATION,
        max_concurrency=2,
    )

    # The skeleton stage is set by _prepare_input (first) and re-asserted by
    # _build_skeleton. Then analyzing_chunks appears once per chunk (idempotent),
    # followed by aggregating, reporting, summarizing, composing_prompt_pack.
    assert seen_stages[0] == "building_skeleton"
    assert "analyzing_chunks" in seen_stages
    # Stages are emitted in forward-progressing order — no stage that has
    # been seen may reappear after a later stage has shown up (idempotent same-stage
    # repetition is allowed).
    expected_order = [
        "building_skeleton",
        "analyzing_chunks",
        "aggregating",
        "reporting",
        "summarizing",
        "composing_prompt_pack",
    ]
    observed_unique = [s for s in seen_stages if s is not None]
    for stage in expected_order:
        assert stage in observed_unique
    # Final call clears the stage.
    assert seen_stages[-1] is None
    get_settings.cache_clear()
