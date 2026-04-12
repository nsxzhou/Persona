from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from langchain_core.messages import HumanMessage
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.style_analysis_jobs import (
    SECTION_TITLES,
    AnalysisReport,
    ChunkAnalysis,
    MergedAnalysis,
)
from app.services.style_analysis_llm import StructuredLLMClient
from app.services.style_analysis_storage import StyleAnalysisStorageService
from app.services.style_analysis_text import read_chunks_and_classification
from app.services.style_analysis_pipeline import StyleAnalysisPipeline


def build_section(section: str, title: str) -> dict:
    return {
        "section": section,
        "title": title,
        "overview": f"{title}的概览。",
        "findings": [
            {
                "label": f"{title}发现",
                "summary": f"{title}的关键结论。",
                "frequency": "当前样本中出现 1 次",
                "confidence": "medium",
                "is_weak_judgment": False,
                "evidence": [{"excerpt": "夜色很冷。", "location": "段落 1"}],
            }
        ],
    }


def build_report_payload(*, sections: list[dict] | None = None) -> dict:
    return {
        "executive_summary": {
            "summary": "整体文风冷峻、短句密集。",
            "representative_evidence": [{"excerpt": "夜色很冷。", "location": "段落 1"}],
        },
        "basic_assessment": {
            "text_type": "章节正文",
            "multi_speaker": False,
            "batch_mode": False,
            "location_indexing": "章节或段落位置",
            "noise_handling": "未发现显著噪声。",
        },
        "sections": sections
        if sections is not None
        else [build_section(section, title) for section, title in SECTION_TITLES],
        "appendix": None,
    }


def test_section_titles_cover_expected_dossier_sections_in_order() -> None:
    assert SECTION_TITLES == [
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


@pytest.mark.parametrize(
    "sections",
    [
        [build_section(section, title) for section, title in SECTION_TITLES[:-1]],
        [build_section("3.2", "固定句式与节奏偏好")]
        + [build_section("3.1", "口头禅与常用表达")]
        + [build_section(section, title) for section, title in SECTION_TITLES[2:]],
        [build_section(section, title) for section, title in SECTION_TITLES[:-1]]
        + [build_section("3.11", "常见场景的说话方式")],
    ],
)
def test_analysis_report_rejects_missing_reordered_or_duplicate_sections(
    sections: list[dict],
) -> None:
    with pytest.raises(ValidationError, match="sections must cover 3.1 through 3.12"):
        AnalysisReport.model_validate(build_report_payload(sections=sections))


def test_chunk_and_merged_analysis_share_section_validation() -> None:
    valid_sections = [build_section(section, title) for section, title in SECTION_TITLES]
    chunk = ChunkAnalysis.model_validate(
        {"chunk_index": 0, "chunk_count": 1, "sections": valid_sections}
    )
    merged = MergedAnalysis.model_validate(
        {"classification": {"text_type": "章节正文"}, "sections": valid_sections}
    )

    assert chunk.sections[0].section == "3.1"
    assert merged.sections[-1].section == "3.12"

    with pytest.raises(ValidationError, match="sections must cover 3.1 through 3.12"):
        ChunkAnalysis.model_validate(
            {"chunk_index": 0, "chunk_count": 1, "sections": valid_sections[:-1]}
        )


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
async def test_structured_llm_client_wraps_model_with_strict_json_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    get_settings.cache_clear()

    class FakeStructuredRunnable:
        async def ainvoke(self, messages: list[HumanMessage]) -> AnalysisReport:
            assert len(messages) == 1
            assert messages[0].content == "生成报告"
            return AnalysisReport.model_validate(build_report_payload())

    class FakeModel:
        def __init__(self) -> None:
            self.structured_calls: list[tuple[type, dict]] = []

        def with_structured_output(self, schema: type, **kwargs: object) -> FakeStructuredRunnable:
            self.structured_calls.append((schema, kwargs))
            return FakeStructuredRunnable()

    fake_model = FakeModel()
    factory_calls: list[dict] = []

    def fake_model_factory(**kwargs: object) -> FakeModel:
        factory_calls.append(kwargs)
        return fake_model

    provider = SimpleNamespace(
        base_url="https://api.example.test/v1",
        api_key_encrypted="encrypted-key",
    )
    client = StructuredLLMClient(
        model_factory=fake_model_factory,
        secret_decrypter=lambda value: f"decrypted:{value}",
    )

    model = client.build_model(provider=provider, model_name="gpt-4.1-mini")
    result = await client.ainvoke_structured(
        model=model,
        schema=AnalysisReport,
        prompt="生成报告",
    )

    assert isinstance(result, AnalysisReport)
    assert result.model_dump(mode="json")["sections"][0]["section"] == "3.1"
    assert fake_model.structured_calls == [
        (AnalysisReport, {"method": "json_schema", "strict": True})
    ]
    assert factory_calls == [
        {
            "model": "gpt-4.1-mini",
            "model_provider": "openai",
            "base_url": "https://api.example.test/v1",
            "api_key": "decrypted:encrypted-key",
            "temperature": 0.0,
            "timeout": 15.0,
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
            {"chunk_index": index, "sections": [build_section(section, title) for section, title in SECTION_TITLES]},
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
        # First chunk content with chapter headers to force chunking
        # Each chunk needs to be > 50 characters to be emitted, or at the end
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

    chunk_count, character_count, classification = await read_chunks_and_classification(
        stream(),
        on_chunk=on_chunk,
    )

    assert chunk_count == 3
    assert classification["location_indexing"] == "章节或段落位置"


@pytest.mark.asyncio
async def test_pipeline_merge_chunks_reduces_batches_incrementally() -> None:
    class FakeStorageService:
        async def read_chunk_analysis_batches(self, job_id: str, *, batch_size: int):
            del job_id, batch_size
            sections = [build_section(section, title) for section, title in SECTION_TITLES]
            yield [
                {"chunk_index": 0, "chunk_count": 10, "sections": sections},
                {"chunk_index": 1, "chunk_count": 10, "sections": sections},
            ]
            yield [
                {"chunk_index": 2, "chunk_count": 10, "sections": sections},
                {"chunk_index": 3, "chunk_count": 10, "sections": sections},
            ]

    class FakeMergeClient:
        def __init__(self) -> None:
            self.merge_calls = 0

        def build_model(self, *, provider: object, model_name: str) -> object:
            return SimpleNamespace(provider=provider, model_name=model_name)

        async def ainvoke_structured(self, *, model: object, schema: type, prompt: str):
            del model, prompt
            assert schema is MergedAnalysis
            self.merge_calls += 1
            return MergedAnalysis.model_validate(
                {
                    "classification": {"text_type": "章节正文"},
                    "sections": [build_section(section, title) for section, title in SECTION_TITLES],
                }
            )

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
    assert merged["merged_analysis"]["sections"][0]["section"] == "3.1"
