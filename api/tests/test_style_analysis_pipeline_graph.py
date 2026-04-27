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


def build_voice_profile_markdown() -> str:
    return (
        "# Voice Profile\n"
        "## 3.1 口头禅与常用表达\n- 执行规则：短句推进，反问收束。\n\n"
        "## 3.2 固定句式与节奏偏好\n- 执行规则：短句抢拍，长句补判断。\n\n"
        "## 3.3 词汇选择偏好\n- 执行规则：混用现代术语与古典四字格。\n\n"
        "## 3.4 句子构造习惯\n- 执行规则：句首落判断，句尾短断语。\n\n"
        "## 3.5 生活经历线索\n- 执行规则：生活线索弱，偏商业管理语境。\n\n"
        "## 3.6 行业／地域词汇\n- 执行规则：行业词集中在运营、渠道、成本收益。\n\n"
        "## 3.7 自然化缺陷\n- 执行规则：保留省略、跳接、省略号停顿。\n\n"
        "## 3.8 写作忌口与避讳\n- 执行规则：少写解释性开场和总结升华。\n\n"
        "## 3.9 比喻口味与意象库\n- 执行规则：意象偏月色、视线、掌心。\n\n"
        "## 3.10 思维模式与表达逻辑\n- 执行规则：观察、质疑、类比、结论递进。\n\n"
        "## 3.11 常见场景的说话方式\n- 执行规则：对白抢拍、试探、调侃。\n\n"
        "## 3.12 个人价值取向与反复母题\n- 执行规则：强调效率、交易和掌控。\n"
    )


class PipelineLLMStub:
    def __init__(self, *, fail_report_once: bool = False) -> None:
        self.active_chunks = 0
        self.max_active_chunks = 0
        self.chunk_calls = 0
        self.report_calls = 0
        self.fail_report_once = fail_report_once

    async def invoke_markdown_completion(
        self,
        *,
        provider_config: object | None = None,
        prompt: str,
        model_name: str | None = None,
        injection_task: object | None = None,
    ) -> str:
        del provider_config, model_name, injection_task
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
        if "Voice Profile" in prompt:
            return build_voice_profile_markdown()
        return build_report_markdown()


def build_pipeline(client: PipelineLLMStub, checkpointer: InMemorySaver) -> StyleAnalysisPipeline:
    return StyleAnalysisPipeline(
        provider=SimpleNamespace(base_url="https://api.example.test/v1", api_key_encrypted="encrypted"),
        model_name="gpt-4.1-mini",
        style_name="古龙风格实验",
        source_filename="sample.txt",
        llm_service=client,
        checkpointer=checkpointer,
    )


@pytest.mark.asyncio
async def test_pipeline_graph_limits_chunk_concurrency_and_returns_voice_profile(
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
    assert result.voice_profile_markdown.startswith("# Voice Profile")
    assert "## 3.1 口头禅与常用表达" in result.voice_profile_markdown
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

    result = await pipeline.run(**kwargs)

    assert client.chunk_calls == 3
    assert client.report_calls == 2
    assert result.voice_profile_markdown.startswith("# Voice Profile")
    assert "## 3.12 个人价值取向与反复母题" in result.voice_profile_markdown
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
                "voice_profile_markdown": build_voice_profile_markdown(),
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
    assert result.voice_profile_markdown.startswith("# Voice Profile")
    get_settings.cache_clear()
