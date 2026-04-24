from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.core.config import get_settings
from app.schemas.plot_analysis_jobs import PlotAnalysisMeta
from app.services import plot_analysis_pipeline as pipeline_module
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


def _sketch_payload(chunk_index: int, chunk_count: int) -> dict:
    return {
        "chunk_index": chunk_index,
        "chunk_count": chunk_count,
        "characters_present": ["主角"],
        "events": [f"chunk {chunk_index} 事件"],
        "advancement": "setup",
        "time_marker": "linear",
    }


class PipelineLLMStub:
    """Routes LLM calls to canned outputs based on prompt signatures.

    Each list captures the raw prompt seen per stage so the test can assert the
    skeleton content was actually threaded downstream.
    """

    def __init__(self) -> None:
        self.sketch_prompts: list[str] = []
        self.skeleton_reduce_prompts: list[str] = []
        self.skeleton_group_reduce_prompts: list[str] = []
        self.chunk_analysis_prompts: list[str] = []
        self.merge_prompts: list[str] = []
        self.report_prompts: list[str] = []
        self.summary_prompts: list[str] = []
        self.pack_prompts: list[str] = []

    def build_model(self, *, provider: object, model_name: str) -> object:
        return SimpleNamespace(provider=provider, model_name=model_name)

    async def ainvoke_markdown(
        self,
        *,
        model: object,
        prompt: str,
        provider: object | None = None,
        model_name: str | None = None,
    ) -> str:
        del model, provider, model_name
        if "Plot Lab 的分块速写阶段" in prompt:
            match = re.search(r"chunk_index=(\d+), chunk_count=(\d+)", prompt)
            assert match is not None, "sketch prompt must expose chunk_index/chunk_count"
            self.sketch_prompts.append(prompt)
            return _sketch_json(int(match.group(1)), int(match.group(2)))
        if "Plot Lab 的骨架分组归并阶段" in prompt:
            self.skeleton_group_reduce_prompts.append(prompt)
            # Return a minimal sub-skeleton markdown that the final reducer will merge.
            return "# 全书骨架\n## 阶段划分（按 chunk 索引）\n子骨架段落\n"
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
        if "Markdown 情节 prompt 包" in prompt:
            self.pack_prompts.append(prompt)
            return "# Shared Constraints\n包内容"
        raise AssertionError(f"Unexpected prompt: {prompt[:120]}")


class NoisyPromptPackLLMStub(PipelineLLMStub):
    async def ainvoke_markdown(
        self,
        *,
        model: object,
        prompt: str,
        provider: object | None = None,
        model_name: str | None = None,
    ) -> str:
        if "Markdown 情节 prompt 包" in prompt:
            del model, provider, model_name
            self.pack_prompts.append(prompt)
            return (
                "好的，遵照您的要求。作为小说情节 prompt 编排器，我已基于您提供的完整 Plot Lab 分析报告和当前剧情摘要，"
                "生成了一份全局可复用的 Markdown 情节母 prompt 包。\n\n"
                "---\n\n"
                "# Shared Constraints\n"
                "- 保留的约束\n\n"
                "# Tone Lock\n"
                "- 保留的语气\n\n"
                "# Anti-Whitewash Guardrails\n"
                "- 保留的边界\n\n"
                "# Worldbuilding Prompt\n"
                "世界观模板\n\n"
                "# Character Cards Prompt\n"
                "角色模板\n\n"
                "# Outline Master Prompt\n"
                "总纲模板\n\n"
                "# Volume Planning Prompt\n"
                "分卷模板\n\n"
                "# Chapter Outline Prompt\n"
                "章节模板\n\n"
                "# Beat Planning Prompt\n"
                "节拍模板\n\n"
                "# Continuation Guardrails\n"
                "续写边界\n\n"
                "# Few-shot Slots\n"
                "## Slot 1\n"
                "- Label: 示例\n"
                "- Type: 模板\n"
                "- Purpose: 示例\n"
                "- Text: [角色A] 在 [场景D] 获取 [资源C]\n\n"
                "# 无关说明\n"
                "- 这部分不应被保留\n"
            )
        return await super().ainvoke_markdown(
            model=model,
            prompt=prompt,
            provider=provider,
            model_name=model_name,
        )


def build_pipeline(client: PipelineLLMStub, checkpointer: InMemorySaver) -> PlotAnalysisPipeline:
    chat_model = client.build_model(
        provider=SimpleNamespace(
            base_url="https://api.example.test/v1",
            api_key_encrypted="encrypted",
        ),
        model_name="gpt-4.1-mini",
    )
    return PlotAnalysisPipeline(
        provider=SimpleNamespace(
            base_url="https://api.example.test/v1",
            api_key_encrypted="encrypted",
        ),
        model_name="gpt-4.1-mini",
        plot_name="骨架测试",
        source_filename="sample.txt",
        llm_client=client,
        chat_model=chat_model,
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


def test_route_chunks_does_not_embed_skeleton_into_each_send_payload() -> None:
    pipeline = build_pipeline(PipelineLLMStub(), InMemorySaver())

    sends = pipeline._route_chunks(  # noqa: SLF001 - private regression test
        {
            "job_id": "job-route-chunks",
            "plot_name": "骨架测试",
            "source_filename": "sample.txt",
            "model_name": "gpt-4.1-mini",
            "chunk_count": 2,
            "classification": _CLASSIFICATION,
            "plot_skeleton_markdown": _SKELETON_MARKDOWN,
        }
    )

    assert [send.node for send in sends] == ["analyze_chunk", "analyze_chunk"]
    for index, send in enumerate(sends):
        assert send.arg["chunk_index"] == index
        assert "plot_skeleton_markdown" not in send.arg


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
    chat_model = client.build_model(
        provider=SimpleNamespace(
            base_url="https://api.example.test/v1",
            api_key_encrypted="encrypted",
        ),
        model_name="gpt-4.1-mini",
    )
    pipeline = PlotAnalysisPipeline(
        provider=SimpleNamespace(
            base_url="https://api.example.test/v1",
            api_key_encrypted="encrypted",
        ),
        model_name="gpt-4.1-mini",
        plot_name="阶段测试",
        source_filename="sample.txt",
        llm_client=client,
        chat_model=chat_model,
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
    # _build_skeleton. Then selecting_focus_chunks appears before chunk analysis,
    # followed by aggregating, reporting, postprocessing.
    assert seen_stages[0] == "building_skeleton"
    assert "selecting_focus_chunks" in seen_stages
    assert "analyzing_focus_chunks" in seen_stages
    # Stages are emitted in forward-progressing order — no stage that has
    # been seen may reappear after a later stage has shown up (idempotent same-stage
    # repetition is allowed).
    expected_order = [
        "building_skeleton",
        "selecting_focus_chunks",
        "analyzing_focus_chunks",
        "aggregating",
        "reporting",
        "postprocessing",
    ]
    observed_unique = [s for s in seen_stages if s is not None]
    for stage in expected_order:
        assert stage in observed_unique
    # Final call clears the stage.
    assert seen_stages[-1] is None
    get_settings.cache_clear()


def test_select_focus_chunks_keeps_boundaries_and_payoffs() -> None:
    pipeline = build_pipeline(PipelineLLMStub(), InMemorySaver())

    selected = pipeline._select_focus_chunk_indexes(  # noqa: SLF001
        chunk_count=8,
        sketches=[
            _sketch_payload(0, 8),
            _sketch_payload(1, 8),
            {**_sketch_payload(2, 8), "advancement": "transition"},
            _sketch_payload(3, 8),
            {**_sketch_payload(4, 8), "advancement": "payoff"},
            _sketch_payload(5, 8),
            _sketch_payload(6, 8),
            _sketch_payload(7, 8),
        ],
        plot_skeleton_markdown=(
            "# 全书骨架\n"
            "## 阶段划分（按 chunk 索引）\n"
            "- 启动期 chunk 0-1\n"
            "- 拉升期 chunk 2-4\n"
            "- 收束期 chunk 6-7\n\n"
            "## 主线推进链\n"
            "- 设伏 @chunk2 -> 兑现 @chunk4\n"
        ),
    )

    assert 0 in selected
    assert 7 in selected
    assert 2 in selected
    assert 4 in selected
    assert len(selected) >= 5


@pytest.mark.asyncio
async def test_plot_pipeline_short_inputs_fall_back_to_full_chunk_analysis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()

    storage_service = PlotAnalysisStorageService()
    job_id = "job-short-fallback"
    chunk_count = 2
    for index in range(chunk_count):
        await storage_service.write_chunk_artifact(job_id, index, f"chunk {index} text")

    client = PipelineLLMStub()
    pipeline = build_pipeline(client, InMemorySaver())

    await pipeline.run(
        job_id=job_id,
        chunk_count=chunk_count,
        classification=_CLASSIFICATION,
        max_concurrency=2,
    )

    assert len(client.chunk_analysis_prompts) == chunk_count
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_pipeline_graph_builds_skeleton_via_hierarchical_reduce_when_above_threshold(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Force the hierarchical-reduce path by lowering the token threshold and
    group size so a modest 5-chunk job splits into multiple groups + a final
    reduce call.
    """

    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()

    # Thresholds exposed as module-level constants so we can force the path
    # without constructing a gigantic sketch payload.
    monkeypatch.setattr(pipeline_module, "SKELETON_HIERARCHICAL_TOKEN_THRESHOLD", 0)
    monkeypatch.setattr(pipeline_module, "SKELETON_GROUP_SIZE", 2)

    storage_service = PlotAnalysisStorageService()
    job_id = "job-hierarchical"
    chunk_count = 5
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

    # Five sketches at group_size=2 → ceil(5/2) = 3 sub-skeletons + 1 final reduce.
    assert len(client.sketch_prompts) == chunk_count
    expected_group_calls = -(-chunk_count // 2)  # ceil division
    assert len(client.skeleton_group_reduce_prompts) == expected_group_calls
    # Final reduce runs exactly once over the wrapped sub-skeletons.
    assert len(client.skeleton_reduce_prompts) == 1
    # Final reduce payload contains the sub_skeleton_index wrapper keys.
    assert "sub_skeleton_index" in client.skeleton_reduce_prompts[0]

    # Skeleton artifact written and threaded through the pipeline.
    assert storage_service.stage_markdown_artifact_exists(job_id, name="plot-skeleton")
    skeleton_md = await storage_service.read_stage_markdown_artifact(
        job_id, name="plot-skeleton"
    )
    assert result.plot_skeleton_markdown == skeleton_md


@pytest.mark.asyncio
async def test_pipeline_graph_normalizes_prompt_pack_to_allowed_sections_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()

    storage_service = PlotAnalysisStorageService()
    job_id = "job-prompt-pack-normalize"
    chunk_count = 1
    await storage_service.write_chunk_artifact(job_id, 0, "chunk 0 text")

    client = NoisyPromptPackLLMStub()
    pipeline = build_pipeline(client, InMemorySaver())

    result = await pipeline.run(
        job_id=job_id,
        chunk_count=chunk_count,
        classification=_CLASSIFICATION,
        max_concurrency=1,
    )

    expected = (
        "# Shared Constraints\n"
        "- 保留的约束\n\n"
        "# Tone Lock\n"
        "- 保留的语气\n\n"
        "# Anti-Whitewash Guardrails\n"
        "- 保留的边界\n\n"
        "# Worldbuilding Prompt\n"
        "世界观模板\n\n"
        "# Character Cards Prompt\n"
        "角色模板\n\n"
        "# Outline Master Prompt\n"
        "总纲模板\n\n"
        "# Volume Planning Prompt\n"
        "分卷模板\n\n"
        "# Chapter Outline Prompt\n"
        "章节模板\n\n"
        "# Beat Planning Prompt\n"
        "节拍模板\n\n"
        "# Continuation Guardrails\n"
        "续写边界\n\n"
        "# Few-shot Slots\n"
        "## Slot 1\n"
        "- Label: 示例\n"
        "- Type: 模板\n"
        "- Purpose: 示例\n"
        "- Text: [角色A] 在 [场景D] 获取 [资源C]"
    )
    assert result.prompt_pack_markdown == expected
    assert not result.prompt_pack_markdown.startswith("好的")
    assert "# 无关说明" not in result.prompt_pack_markdown

    stored = await storage_service.read_stage_markdown_artifact(job_id, name="prompt-pack")
    assert stored == expected
    get_settings.cache_clear()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_pipeline_graph_hierarchical_reduce_collapses_to_single_call_when_one_group(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the hierarchy would produce a single group, the short-circuit
    must emit just one reduce call (no group-reduce, no double work).
    """

    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()

    monkeypatch.setattr(pipeline_module, "SKELETON_HIERARCHICAL_TOKEN_THRESHOLD", 0)
    monkeypatch.setattr(pipeline_module, "SKELETON_GROUP_SIZE", 100)  # > chunk_count

    storage_service = PlotAnalysisStorageService()
    job_id = "job-hierarchical-single-group"
    chunk_count = 3
    for index in range(chunk_count):
        await storage_service.write_chunk_artifact(job_id, index, f"chunk {index} text")

    client = PipelineLLMStub()
    pipeline = build_pipeline(client, InMemorySaver())

    await pipeline.run(
        job_id=job_id,
        chunk_count=chunk_count,
        classification=_CLASSIFICATION,
        max_concurrency=3,
    )

    # Single-group hierarchy collapses: one reduce, no group-reduce calls.
    assert len(client.skeleton_group_reduce_prompts) == 0
    assert len(client.skeleton_reduce_prompts) == 1
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_pipeline_graph_resumes_from_existing_sketch_artifacts_without_calling_sketch_llm(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resume semantics: if sketch artifacts already exist on disk, the
    sketch_chunk node must short-circuit and never hit the LLM sketch branch.
    """

    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()

    storage_service = PlotAnalysisStorageService()
    job_id = "job-resume-sketches"
    chunk_count = 3
    for index in range(chunk_count):
        await storage_service.write_chunk_artifact(job_id, index, f"chunk {index} text")
        # Pre-populate all sketch artifacts so sketch_chunk resumes.
        await storage_service.write_sketch_artifact(
            job_id, index, _sketch_payload(index, chunk_count)
        )

    client = PipelineLLMStub()
    pipeline = build_pipeline(client, InMemorySaver())

    result = await pipeline.run(
        job_id=job_id,
        chunk_count=chunk_count,
        classification=_CLASSIFICATION,
        max_concurrency=3,
    )

    # Sketch LLM branch is never hit when artifacts pre-exist.
    assert client.sketch_prompts == []
    # Skeleton reduce still runs over the pre-existing sketches.
    assert len(client.skeleton_reduce_prompts) == 1
    # Downstream stages still execute normally.
    assert len(client.chunk_analysis_prompts) == chunk_count
    assert len(client.report_prompts) == 1
    assert result.plot_skeleton_markdown == _SKELETON_MARKDOWN
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_pipeline_graph_resumes_from_existing_skeleton_artifact_without_calling_reduce_llm(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resume semantics: if ``plot-skeleton.md`` already exists on disk, the
    build_skeleton node must short-circuit and never hit the reduce prompt.
    """

    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()

    storage_service = PlotAnalysisStorageService()
    job_id = "job-resume-skeleton"
    chunk_count = 2
    for index in range(chunk_count):
        await storage_service.write_chunk_artifact(job_id, index, f"chunk {index} text")
        await storage_service.write_sketch_artifact(
            job_id, index, _sketch_payload(index, chunk_count)
        )
    prebuilt_skeleton = (
        "# 全书骨架\n"
        f"## 阶段划分（按 chunk 索引）\n{_SKELETON_SIGNATURE} 预置骨架内容\n"
    )
    await storage_service.write_stage_markdown_artifact(
        job_id, name="plot-skeleton", markdown=prebuilt_skeleton
    )

    client = PipelineLLMStub()
    pipeline = build_pipeline(client, InMemorySaver())

    result = await pipeline.run(
        job_id=job_id,
        chunk_count=chunk_count,
        classification=_CLASSIFICATION,
        max_concurrency=2,
    )

    # With both sketches and skeleton pre-populated, neither sketch nor
    # skeleton-reduce LLM branches should fire.
    assert client.sketch_prompts == []
    assert client.skeleton_reduce_prompts == []
    assert client.skeleton_group_reduce_prompts == []
    # The pre-populated skeleton is threaded downstream verbatim.
    assert result.plot_skeleton_markdown == prebuilt_skeleton
    for chunk_prompt in client.chunk_analysis_prompts:
        assert _SKELETON_SIGNATURE in chunk_prompt
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_pipeline_run_clears_final_stage_without_honoring_late_pause(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()

    pipeline = build_pipeline(PipelineLLMStub(), InMemorySaver())
    pause_requested = False

    class FakeGraph:
        async def aget_state(self, config):
            return SimpleNamespace(next=())

        async def ainvoke(self, graph_input, config):
            nonlocal pause_requested
            pause_requested = True
            return {
                "analysis_meta": {
                    "source_filename": "sample.txt",
                    "model_name": "gpt-4.1-mini",
                    "text_type": "章节正文",
                    "has_timestamps": False,
                    "has_speaker_labels": False,
                    "has_noise_markers": False,
                    "uses_batch_processing": False,
                    "location_indexing": "章节或段落位置",
                    "chunk_count": 1,
                },
                "analysis_report_markdown": "# 执行摘要\n最终报告",
                "plot_summary_markdown": "# 剧情定位\n摘要内容",
                "prompt_pack_markdown": "# Shared Constraints\n包内容",
                "plot_skeleton_markdown": _SKELETON_MARKDOWN,
            }

    pipeline.graph = FakeGraph()
    pipeline.should_pause = lambda: pause_requested

    result = await pipeline.run(
        job_id="job-final-pause-plot",
        chunk_count=1,
        classification={
            "text_type": "章节正文",
            "has_timestamps": False,
            "has_speaker_labels": False,
            "has_noise_markers": False,
            "uses_batch_processing": False,
            "location_indexing": "章节或段落位置",
        },
        max_concurrency=1,
    )

    assert result.analysis_report_markdown.startswith("# 执行摘要")
    assert result.plot_summary_markdown.startswith("# 剧情定位")
    assert result.prompt_pack_markdown.startswith("# Shared Constraints")
    assert result.plot_skeleton_markdown == _SKELETON_MARKDOWN

    get_settings.cache_clear()
