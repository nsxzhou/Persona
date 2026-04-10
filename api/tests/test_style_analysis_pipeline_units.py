from __future__ import annotations

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


@pytest.mark.asyncio
async def test_structured_llm_client_invokes_pydantic_schema_with_strict_json_schema(
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

    result = await client.ainvoke_structured(
        provider=provider,
        model_name="gpt-4.1-mini",
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
