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
from app.services.llm_provider import LLMProviderService
from app.services.plot_analysis_pipeline import PlotAnalysisPipeline
from app.services.plot_analysis_storage import PlotAnalysisStorageService
from app.services.prompt_injection_policy import PromptInjectionTask


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
            "scene_units": [f"chunk {chunk_index} 场景：主角被压力推入行动"],
            "main_events": [f"chunk {chunk_index} 事件"],
            "side_threads": [],
            "payoff_points": ["小反击"],
            "tension_points": ["压力升级"],
            "hooks": ["局面未解"],
            "setup_payoff_links": ["压力铺垫 -> 小反击"],
            "pacing_shift": "压迫转入行动",
            "time_marker": "linear",
            "sample_coverage": ["development_seen"],
        },
        ensure_ascii=False,
    )


class PipelineLLMStub:
    def __init__(self) -> None:
        self.sketch_prompts: list[str] = []
        self.skeleton_reduce_prompts: list[str] = []
        self.skeleton_group_reduce_prompts: list[str] = []
        self.chunk_analysis_prompts: list[str] = []
        self.merge_prompts: list[str] = []
        self.report_prompts: list[str] = []
        self.story_engine_prompts: list[str] = []

    async def invoke_markdown_completion(
        self,
        *,
        provider_config: object | None = None,
        prompt: str,
        model_name: str | None = None,
        injection_task: object | None = None,
    ) -> str:
        del provider_config, model_name, injection_task
        if "Plot Lab 的分块速写阶段" in prompt:
            match = re.search(r"chunk_index=(\d+), chunk_count=(\d+)", prompt)
            assert match is not None
            self.sketch_prompts.append(prompt)
            return _sketch_json(int(match.group(1)), int(match.group(2)))
        if "Plot Lab 的骨架分组归并阶段" in prompt:
            self.skeleton_group_reduce_prompts.append(prompt)
            return "# 全书骨架\n## 阶段划分（按 chunk 索引）\n子骨架段落\n"
        if "Plot Lab 的样本骨架聚合阶段" in prompt:
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
            return "# 执行摘要\n最终报告\n\n## 2.5.1 主线剧情分析\n- 样本内主线推进。"
        if "Plot Writing Guide" in prompt:
            self.story_engine_prompts.append(prompt)
            return (
                "# Plot Writing Guide\n"
                "## Core Plot Formula\n- 用压力迫使主角行动。\n\n"
                "## Chapter Progression Loop\n- 目标 -> 阻碍 -> 行动 -> 小兑现 -> 新压力。\n\n"
                "## Scene Construction Rules\n- 每场必须改变局面。\n\n"
                "## Setup and Payoff Rules\n- 伏笔必须参与行动兑现。\n\n"
                "## Payoff and Tension Rhythm\n- 半兑现后追加更大压力。\n\n"
                "## Side Plot Usage\n- 支线回流主线。\n\n"
                "## Hook Recipes\n- 胜利后揭示代价。\n\n"
                "## Anti-Drift Rules\n- 不要复述样本剧情。\n"
            )
        raise AssertionError(f"Unexpected prompt: {prompt[:120]}")


class NoisyStoryEngineLLMStub(PipelineLLMStub):
    async def invoke_markdown_completion(self, **kwargs) -> str:
        prompt = kwargs["prompt"]
        if "Plot Writing Guide" in prompt:
            self.story_engine_prompts.append(prompt)
            return (
                "好的，下面开始。\n\n"
                "# Plot Writing Guide\n"
                "## Core Plot Formula\n- 以身份压力制造行动。\n\n"
                "## Chapter Progression Loop\n- 目标 -> 阻碍 -> 行动 -> 反转。\n\n"
                "## Scene Construction Rules\n- 场景结尾改变筹码。\n\n"
                "## Setup and Payoff Rules\n- 伏笔在行动中兑现。\n\n"
                "## Payoff and Tension Rhythm\n- 反杀后立刻加码。\n\n"
                "## Side Plot Usage\n- 支线提供反讽对照。\n\n"
                "## Hook Recipes\n- 信息揭晓后立刻选择。\n\n"
                "## Anti-Drift Rules\n- 不要解释规则。\n\n"
                "# 无关说明\n- 这里不应保留\n"
            )
        return await super().invoke_markdown_completion(**kwargs)


def build_pipeline(client: PipelineLLMStub, checkpointer: InMemorySaver) -> PlotAnalysisPipeline:
    return PlotAnalysisPipeline(
        provider=SimpleNamespace(base_url="https://api.example.test/v1", api_key_encrypted="encrypted"),
        model_name="gpt-4.1-mini",
        plot_name="骨架测试",
        source_filename="sample.txt",
        llm_service=client,
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
async def test_pipeline_graph_builds_report_and_plot_writing_guide_without_chunk_deep_analysis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()

    storage_service = PlotAnalysisStorageService()
    job_id = "job-skeleton-threading"
    chunk_count = 3
    for index in range(chunk_count):
        await storage_service.write_chunk_artifact(job_id, index, f"chunk {index} text")

    client = PipelineLLMStub()
    pipeline = build_pipeline(client, InMemorySaver())

    result = await pipeline.run(
        job_id=job_id,
        chunk_count=chunk_count,
        classification=_CLASSIFICATION,
        max_concurrency=2,
    )

    assert len(client.skeleton_reduce_prompts) == 1
    assert len(client.chunk_analysis_prompts) == 0
    assert len(client.merge_prompts) == 0
    assert _SKELETON_SIGNATURE in client.report_prompts[0]
    assert result.story_engine_markdown.startswith("# Plot Writing Guide")
    assert "## Core Plot Formula" in result.story_engine_markdown
    assert result.plot_skeleton_markdown == _SKELETON_MARKDOWN
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
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_pipeline_graph_normalizes_plot_writing_guide_to_allowed_sections_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()

    storage_service = PlotAnalysisStorageService()
    job_id = "job-story-engine-normalize"
    await storage_service.write_chunk_artifact(job_id, 0, "chunk 0 text")

    client = NoisyStoryEngineLLMStub()
    pipeline = build_pipeline(client, InMemorySaver())

    result = await pipeline.run(
        job_id=job_id,
        chunk_count=1,
        classification=_CLASSIFICATION,
        max_concurrency=1,
    )

    assert result.story_engine_markdown.startswith("# Plot Writing Guide")
    assert "# 无关说明" not in result.story_engine_markdown
    assert "## Core Plot Formula" in result.story_engine_markdown
    stored = await storage_service.read_stage_markdown_artifact(job_id, name="story-engine")
    assert stored == result.story_engine_markdown
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_pipeline_graph_uses_hierarchical_skeleton_reduce_when_forced(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()
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

    assert len(client.sketch_prompts) == chunk_count
    assert len(client.skeleton_group_reduce_prompts) == 3
    assert len(client.skeleton_reduce_prompts) == 1
    assert result.plot_skeleton_markdown == _SKELETON_MARKDOWN
    get_settings.cache_clear()
