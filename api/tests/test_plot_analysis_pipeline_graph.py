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
    def __init__(self) -> None:
        self.sketch_prompts: list[str] = []
        self.skeleton_reduce_prompts: list[str] = []
        self.skeleton_group_reduce_prompts: list[str] = []
        self.chunk_analysis_prompts: list[str] = []
        self.merge_prompts: list[str] = []
        self.report_prompts: list[str] = []
        self.story_engine_prompts: list[str] = []

    def build_model(self, *, provider: object, model_name: str) -> object:
        return SimpleNamespace(provider=provider, model_name=model_name)

    async def ainvoke_markdown(
        self,
        *,
        model: object,
        prompt: str,
        provider: object | None = None,
        model_name: str | None = None,
        injection_task: object | None = None,
    ) -> str:
        del model, provider, model_name, injection_task
        if "Plot Lab 的分块速写阶段" in prompt:
            match = re.search(r"chunk_index=(\d+), chunk_count=(\d+)", prompt)
            assert match is not None
            self.sketch_prompts.append(prompt)
            return _sketch_json(int(match.group(1)), int(match.group(2)))
        if "Plot Lab 的骨架分组归并阶段" in prompt:
            self.skeleton_group_reduce_prompts.append(prompt)
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
        if "Story Engine Profile" in prompt:
            self.story_engine_prompts.append(prompt)
            return (
                "# Story Engine Profile\n"
                "## genre_mother\n- xianxia\n\n"
                "## drive_axes\n- 升级\n- 掠夺\n\n"
                "## payoff_objects\n- 力量\n- 资源\n\n"
                "## pressure_formulas\n- 宗门压制 -> 反制夺位\n\n"
                "## relation_roles\n- 奖励源\n- 压迫源\n\n"
                "## scene_verbs\n- 入局\n- 压制\n- 试探\n\n"
                "## hook_recipes\n- 半兑现后追加新压力\n\n"
                "## anti_drift_guardrails\n- 不要退化成纯气氛描写\n\n"
                "## suggested_overlays\n- harem_collect\n- hypnosis_control\n"
            )
        raise AssertionError(f"Unexpected prompt: {prompt[:120]}")


class NoisyStoryEngineLLMStub(PipelineLLMStub):
    async def ainvoke_markdown(self, **kwargs) -> str:
        prompt = kwargs["prompt"]
        if "Story Engine Profile" in prompt:
            self.story_engine_prompts.append(prompt)
            return (
                "好的，下面开始。\n\n"
                "# Story Engine Profile\n"
                "## genre_mother\n- urban\n\n"
                "## drive_axes\n- 逆转\n\n"
                "## payoff_objects\n- 地位\n\n"
                "## pressure_formulas\n- 豪门压制 -> 反杀\n\n"
                "## relation_roles\n- 奖励源\n\n"
                "## scene_verbs\n- 收割\n\n"
                "## hook_recipes\n- 反杀后立刻加码\n\n"
                "## anti_drift_guardrails\n- 不要解释规则\n\n"
                "## suggested_overlays\n- wife_steal\n\n"
                "# 无关说明\n- 这里不应保留\n"
            )
        return await super().ainvoke_markdown(**kwargs)


def build_pipeline(client: PipelineLLMStub, checkpointer: InMemorySaver) -> PlotAnalysisPipeline:
    chat_model = client.build_model(
        provider=SimpleNamespace(base_url="https://api.example.test/v1", api_key_encrypted="encrypted"),
        model_name="gpt-4.1-mini",
    )
    return PlotAnalysisPipeline(
        provider=SimpleNamespace(base_url="https://api.example.test/v1", api_key_encrypted="encrypted"),
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


@pytest.mark.asyncio
async def test_pipeline_graph_threads_skeleton_and_returns_story_engine(
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
    assert len(client.chunk_analysis_prompts) == chunk_count
    assert all(_SKELETON_SIGNATURE in prompt for prompt in client.chunk_analysis_prompts)
    assert _SKELETON_SIGNATURE in client.report_prompts[0]
    assert result.story_engine_markdown.startswith("# Story Engine Profile")
    assert result.suggested_overlays == ["harem_collect", "hypnosis_control"]
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
async def test_pipeline_graph_normalizes_story_engine_to_allowed_sections_only(
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

    assert result.story_engine_markdown.startswith("# Story Engine Profile")
    assert "# 无关说明" not in result.story_engine_markdown
    assert result.suggested_overlays == ["wife_steal"]
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
