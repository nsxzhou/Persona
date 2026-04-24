from __future__ import annotations

import asyncio
import re
from types import SimpleNamespace

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.core.config import get_settings
from app.schemas.style_analysis_jobs import AnalysisMeta
from app.services.style_analysis_pipeline import StyleAnalysisPipeline
from app.services.style_analysis_storage import StyleAnalysisStorageService


def build_report_markdown() -> str:
    return (
        "# 执行摘要\n整体文风冷峻、短句密集。\n\n"
        "# 基础判断\n- 文本类型：章节正文\n\n"
        "# 风格维度\n## 3.1 口头禅与常用表达\n- 夜色很冷。\n"
    )


def build_style_summary_markdown(style_name: str) -> str:
    return f"# 风格名称\n{style_name}\n\n# 风格定位\n冷峻、克制、短句驱动。\n"


def build_prompt_pack_markdown() -> str:
    return "# System Prompt\n以冷峻、克制的中文小说文风进行创作。\n"


class PipelineLLMStub:
    def __init__(self, *, fail_report_once: bool = False) -> None:
        self.active_chunks = 0
        self.max_active_chunks = 0
        self.chunk_calls = 0
        self.report_calls = 0
        self.fail_report_once = fail_report_once

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
        if "当前 chunk：" in prompt:
            match = re.search(r"当前 chunk：(\d+)/(\d+)", prompt)
            assert match is not None
            self.chunk_calls += 1
            self.active_chunks += 1
            self.max_active_chunks = max(self.max_active_chunks, self.active_chunks)
            await asyncio.sleep(0.01)
            self.active_chunks -= 1
            return build_report_markdown()
        if "聚合结果" in prompt:
            self.report_calls += 1
            if self.fail_report_once and self.report_calls == 1:
                raise RuntimeError("report transient failure")
            return build_report_markdown()
        if "风格摘要" in prompt:
            return build_prompt_pack_markdown()
        if "风格名称" in prompt and "分析报告" in prompt:
            return build_style_summary_markdown("古龙风格实验")
        return build_report_markdown()


def build_pipeline(client: PipelineLLMStub, checkpointer: InMemorySaver) -> StyleAnalysisPipeline:
    return StyleAnalysisPipeline(
        provider=SimpleNamespace(base_url="https://api.example.test/v1", api_key_encrypted="encrypted"),
        model_name="gpt-4.1-mini",
        style_name="古龙风格实验",
        source_filename="sample.txt",
        llm_client=client,
        checkpointer=checkpointer,
    )


@pytest.mark.asyncio
async def test_pipeline_graph_limits_chunk_concurrency_with_stubbed_llm(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()

    client = PipelineLLMStub()
    pipeline = build_pipeline(client, InMemorySaver())
    storage_service = StyleAnalysisStorageService()
    job_id = "job-concurrency"
    for index in range(10):
        await storage_service.write_chunk_artifact(job_id, index, f"chunk {index}")

    result = await pipeline.run(
        job_id=job_id,
        chunk_count=10,
        classification={
            "text_type": "章节正文",
            "has_timestamps": False,
            "has_speaker_labels": False,
            "has_noise_markers": False,
            "uses_batch_processing": True,
            "location_indexing": "章节或段落位置",
            "noise_notes": "未发现显著噪声。",
        },
        max_concurrency=3,
    )

    assert client.chunk_calls == 10
    assert client.max_active_chunks <= 3
    assert result.analysis_meta == AnalysisMeta(
        source_filename="sample.txt",
        model_name="gpt-4.1-mini",
        text_type="章节正文",
        has_timestamps=False,
        has_speaker_labels=False,
        has_noise_markers=False,
        uses_batch_processing=True,
        location_indexing="章节或段落位置",
        chunk_count=10,
    )
    assert result.analysis_report_markdown.startswith("# 执行摘要")
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_pipeline_graph_resumes_failed_report_without_reanalyzing_chunks(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()

    checkpointer = InMemorySaver()
    client = PipelineLLMStub(fail_report_once=True)
    pipeline = build_pipeline(client, checkpointer)
    storage_service = StyleAnalysisStorageService()
    job_id = "job-resume"
    for index in range(3):
        await storage_service.write_chunk_artifact(job_id, index, f"chunk {index}")

    kwargs = {
        "job_id": job_id,
        "chunk_count": 3,
        "classification": {
            "text_type": "章节正文",
            "has_timestamps": False,
            "has_speaker_labels": False,
            "has_noise_markers": False,
            "uses_batch_processing": True,
            "location_indexing": "章节或段落位置",
            "noise_notes": "未发现显著噪声。",
        },
        "max_concurrency": 3,
    }

    with pytest.raises(RuntimeError, match="report transient failure"):
        await pipeline.run(**kwargs)

    assert client.chunk_calls == 3
    checkpoint_state = await pipeline.graph.aget_state({"configurable": {"thread_id": job_id}})
    assert "chunks" not in checkpoint_state.values
    assert "chunk_analyses" not in checkpoint_state.values

    result = await pipeline.run(**kwargs)

    assert client.chunk_calls == 3
    assert client.report_calls == 2
    assert result.prompt_pack_markdown.startswith("# System Prompt")
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_pipeline_run_clears_final_stage_without_honoring_late_pause(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()

    client = PipelineLLMStub()
    pipeline = build_pipeline(client, InMemorySaver())
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
                "analysis_report_markdown": build_report_markdown(),
                "style_summary_markdown": build_style_summary_markdown("古龙风格实验"),
                "prompt_pack_markdown": build_prompt_pack_markdown(),
            }

    pipeline.graph = FakeGraph()
    pipeline.should_pause = lambda: pause_requested

    result = await pipeline.run(
        job_id="job-final-pause-style",
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
    assert result.style_summary_markdown.startswith("# 风格名称")
    assert result.prompt_pack_markdown.startswith("# System Prompt")

    get_settings.cache_clear()
