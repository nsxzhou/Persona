from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.style_analysis_jobs import (
    AnalysisMeta,
    ChunkAnalysis,
    MergedAnalysis,
    STYLE_ANALYSIS_REPORT_SECTIONS,
)
from app.services.style_analysis_llm import MarkdownLLMClient
from app.services.style_analysis_storage import StyleAnalysisStorageService
from app.services.style_analysis_text import read_chunks_and_classification
from app.services.style_analysis_pipeline import StyleAnalysisPipeline


def build_chunk_markdown(label: str) -> str:
    return f"# 执行摘要\n{label}\n\n## 3.1 口头禅与常用表达\n- 夜色很冷。\n"


def test_style_analysis_report_sections_cover_expected_titles_in_order() -> None:
    assert STYLE_ANALYSIS_REPORT_SECTIONS == [
        ("3.1", "口头禅与常用表达"),
        ("3.2", "固定句式与节奏偏好"),
        ("3.3", "词汇选择偏好"),
        ("3.4", "句子构造习惯"),
        ("3.5", "生活经历线索"),
        ("3.6", "行业／地域词汇"),
        ("3.7", "自然化缺陷"),
        ("3.8", "写作忌口与避讳"),
        ("3.9", "比喻口味与意象库"),
        ("3.10", "思维模式与表达逻辑"),
        ("3.11", "常见场景的说话方式"),
        ("3.12", "个人价值取向与反复母题"),
    ]


def test_chunk_and_merged_analysis_accept_markdown_payloads() -> None:
    chunk = ChunkAnalysis.model_validate(
        {"chunk_index": 0, "chunk_count": 1, "markdown": build_chunk_markdown("chunk")}
    )
    merged = MergedAnalysis.model_validate(
        {"classification": {"text_type": "章节正文"}, "markdown": build_chunk_markdown("merged")}
    )

    assert chunk.markdown.startswith("# 执行摘要")
    assert "## 3.1 口头禅与常用表达" in merged.markdown


def test_analysis_meta_requires_expected_fields() -> None:
    meta = AnalysisMeta.model_validate(
        {
            "source_filename": "sample.txt",
            "model_name": "gpt-5.4",
            "text_type": "章节正文",
            "has_timestamps": False,
            "has_speaker_labels": False,
            "has_noise_markers": False,
            "uses_batch_processing": True,
            "location_indexing": "章节或段落位置",
            "chunk_count": 3,
        }
    )
    assert meta.chunk_count == 3
    with pytest.raises(ValidationError):
        AnalysisMeta.model_validate({"source_filename": "sample.txt"})


def test_settings_reject_invalid_worker_interval_and_chunk_concurrency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.config import Settings

    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")

    with pytest.raises(ValidationError):
        Settings(PERSONA_STYLE_ANALYSIS_POLL_INTERVAL_SECONDS="0")

    with pytest.raises(ValidationError):
        Settings(PERSONA_STYLE_ANALYSIS_CHUNK_MAX_CONCURRENCY="0")

    with pytest.raises(ValidationError):
        Settings(PERSONA_STYLE_ANALYSIS_CHUNK_MAX_CONCURRENCY="128")


@pytest.mark.asyncio
async def test_structured_llm_client_extracts_markdown_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    get_settings.cache_clear()

    class FakeModel:
        async def ainvoke(self, messages: list[HumanMessage]) -> AIMessage:
            assert len(messages) == 1
            assert messages[0].content == "生成报告"
            return AIMessage(content="# 标题\n正文")

    provider = SimpleNamespace(
        base_url="https://api.example.test/v1",
        api_key_encrypted="encrypted-key",
    )
    factory_calls: list[dict] = []

    def fake_model_factory(**kwargs: object) -> FakeModel:
        factory_calls.append(kwargs)
        return FakeModel()

    client = MarkdownLLMClient(
        model_factory=fake_model_factory,
        secret_decrypter=lambda value: f"decrypted:{value}",
    )
    model = client.build_model(provider=provider, model_name="gpt-4.1-mini")
    result = await client.ainvoke_markdown(model=model, prompt="生成报告")

    assert result == "# 标题\n正文"
    assert factory_calls == [
        {
            "model": "gpt-4.1-mini",
            "model_provider": "openai",
            "base_url": "https://api.example.test/v1",
            "api_key": "decrypted:encrypted-key",
            "temperature": 0.0,
            "timeout": 600.0,
            "max_retries": 2,
        }
    ]
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_storage_service_batches_chunk_analysis_artifacts_and_cleans_job_artifacts(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()
    storage_service = StyleAnalysisStorageService()
    job_id = "job-artifacts"

    await storage_service.write_chunk_artifact(job_id, 0, "chunk-0")
    await storage_service.write_chunk_artifact(job_id, 1, "chunk-1")
    await storage_service.write_chunk_artifact(job_id, 2, "chunk-2")
    assert await storage_service.read_chunk_artifact(job_id, 1) == "chunk-1"

    for index in range(3):
        await storage_service.write_chunk_analysis_artifact(
            job_id,
            index,
            {
                "chunk_index": index,
                "chunk_count": 3,
                "markdown": build_chunk_markdown(f"chunk-{index}"),
            },
        )

    batches = [
        batch
        async for batch in storage_service.read_chunk_analysis_batches(
            job_id,
            batch_size=2,
        )
    ]

    assert [[item["chunk_index"] for item in batch] for batch in batches] == [[0, 1], [2]]

    await storage_service.cleanup_job_artifacts(job_id)
    assert await storage_service.job_artifacts_exist(job_id) is False
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_storage_cleanup_uses_asyncio_to_thread(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()
    storage_service = StyleAnalysisStorageService()
    job_id = "job-cleanup-thread"
    await storage_service.write_chunk_artifact(job_id, 0, "chunk-0")
    assert await storage_service.job_artifacts_exist(job_id) is True

    called: list[tuple[object, tuple, dict]] = []

    async def fake_to_thread(func, /, *args, **kwargs):
        called.append((func, args, kwargs))
        return func(*args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)

    await storage_service.cleanup_job_artifacts(job_id)

    assert called
    assert await storage_service.job_artifacts_exist(job_id) is False
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_read_chunks_and_classification_streams_chunks_via_callback() -> None:
    emitted_chunks: list[tuple[int, str]] = []

    async def stream():
        content = (
            "第一章 开始\n"
            + "这是一段测试文字，用于凑够字数以便触发发射。" * 5 + "\n"
            + "第二章 继续\n"
            + "这是第二段测试文字，用于凑够字数以便触发发射。" * 5 + "\n"
            + "第三章 结束\n"
            + "这是第三段测试文字，用于凑够字数以便触发发射。" * 5
        )
        yield content.encode("utf-8")

    async def on_chunk(index: int, chunk_text: str) -> None:
        emitted_chunks.append((index, chunk_text))

    chunk_count, _character_count, classification = await read_chunks_and_classification(
        stream(),
        on_chunk=on_chunk,
    )

    assert chunk_count == 3
    assert classification["location_indexing"] == "章节或段落位置"


@pytest.mark.asyncio
async def test_pipeline_merge_chunks_reduces_batches_incrementally() -> None:
    class FakeStorageService:
        def stage_markdown_artifact_exists(self, job_id: str, *, name: str) -> bool:
            del job_id, name
            return False

        async def append_job_log(self, job_id: str, message: str) -> None:
            pass

        async def read_chunk_analysis_batches(self, job_id: str, *, batch_size: int):
            del job_id, batch_size
            yield [
                {"chunk_index": 0, "chunk_count": 10, "markdown": build_chunk_markdown("0")},
                {"chunk_index": 1, "chunk_count": 10, "markdown": build_chunk_markdown("1")},
            ]
            yield [
                {"chunk_index": 2, "chunk_count": 10, "markdown": build_chunk_markdown("2")},
                {"chunk_index": 3, "chunk_count": 10, "markdown": build_chunk_markdown("3")},
            ]

        async def write_stage_markdown_artifact(
            self, job_id: str, *, name: str, markdown: str
        ) -> None:
            del job_id, name, markdown

    class FakeMergeClient:
        def __init__(self) -> None:
            self.merge_calls = 0

        def build_model(self, *, provider: object, model_name: str) -> object:
            return SimpleNamespace(provider=provider, model_name=model_name)

        async def ainvoke_markdown(self, *, model: object, prompt: str) -> str:
            del model, prompt
            self.merge_calls += 1
            return build_chunk_markdown(f"merge-{self.merge_calls}")

    client = FakeMergeClient()
    pipeline = StyleAnalysisPipeline(
        provider=SimpleNamespace(base_url="https://api.example.test/v1", api_key_encrypted="encrypted"),
        model_name="gpt-4.1-mini",
        style_name="古龙风格实验",
        source_filename="sample.txt",
        llm_client=client,
    )
    pipeline.storage_service = FakeStorageService()

    merged = await pipeline._merge_chunks(
        {
            "job_id": "job-merge",
            "style_name": "古龙风格实验",
            "source_filename": "sample.txt",
            "model_name": "gpt-4.1-mini",
            "chunk_count": 4,
            "classification": {
                "text_type": "章节正文",
                "has_timestamps": False,
                "has_speaker_labels": False,
                "has_noise_markers": False,
                "uses_batch_processing": True,
                "location_indexing": "章节或段落位置",
                "noise_notes": "未发现显著噪声。",
            },
        }
    )

    assert client.merge_calls == 2
    assert merged["merged_analysis_markdown"].startswith("# 执行摘要")
