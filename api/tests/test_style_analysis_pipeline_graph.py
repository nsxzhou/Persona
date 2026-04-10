from __future__ import annotations

import asyncio
import re
from types import SimpleNamespace

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.schemas.style_analysis_jobs import (
    SECTION_TITLES,
    AnalysisReport,
    ChunkAnalysis,
    MergedAnalysis,
    PromptPack,
    StyleSummary,
)
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


def build_sections() -> list[dict]:
    return [build_section(section, title) for section, title in SECTION_TITLES]


def build_report_payload() -> dict:
    return {
        "executive_summary": {
            "summary": "整体文风冷峻、短句密集。",
            "representative_evidence": [{"excerpt": "夜色很冷。", "location": "段落 1"}],
        },
        "basic_assessment": {
            "text_type": "章节正文",
            "multi_speaker": False,
            "batch_mode": True,
            "location_indexing": "章节或段落位置",
            "noise_handling": "未发现显著噪声。",
        },
        "sections": build_sections(),
        "appendix": None,
    }


def build_style_summary_payload(style_name: str) -> dict:
    return {
        "style_name": style_name,
        "style_positioning": "冷峻、克制、短句驱动。",
        "core_features": ["短句推进", "留白明显"],
        "lexical_preferences": ["冷", "忽然"],
        "rhythm_profile": ["短句为主"],
        "punctuation_profile": ["句号收束多"],
        "imagery_and_themes": ["夜色"],
        "scene_strategies": [{"scene": "dialogue", "instruction": "对白尽量短。"}],
        "avoid_or_rare": ["避免长篇抒情。"],
        "generation_notes": ["保留冷感词和短句节奏。"],
    }


def build_prompt_pack_payload() -> dict:
    return {
        "system_prompt": "以冷峻、克制的中文小说文风进行创作。",
        "scene_prompts": {
            "dialogue": "对白短促。",
            "action": "动作描写利落。",
            "environment": "环境描写服务情绪。",
        },
        "hard_constraints": ["避免现代网络口吻。"],
        "style_controls": {
            "tone": "冷峻克制",
            "rhythm": "短句驱动",
            "evidence_anchor": "优先使用高置信证据",
        },
        "few_shot_slots": [
            {
                "label": "environment",
                "type": "environment",
                "text": "夜色很冷。",
                "purpose": "建立冷感氛围",
            }
        ],
    }


class FakeStructuredLLMClient:
    def __init__(self, *, fail_report_once: bool = False) -> None:
        self.active_chunks = 0
        self.max_active_chunks = 0
        self.chunk_calls = 0
        self.report_calls = 0
        self.fail_report_once = fail_report_once

    async def ainvoke_structured(
        self,
        *,
        provider: object,
        model_name: str,
        schema: type,
        prompt: str,
    ) -> object:
        del provider, model_name
        if schema is ChunkAnalysis:
            match = re.search(r"当前 chunk：(\d+)/(\d+)", prompt)
            assert match is not None
            chunk_index = int(match.group(1)) - 1
            chunk_count = int(match.group(2))
            self.chunk_calls += 1
            self.active_chunks += 1
            self.max_active_chunks = max(self.max_active_chunks, self.active_chunks)
            await asyncio.sleep(0.01)
            self.active_chunks -= 1
            return ChunkAnalysis.model_validate(
                {
                    "chunk_index": chunk_index,
                    "chunk_count": chunk_count,
                    "sections": build_sections(),
                }
            )
        if schema is MergedAnalysis:
            return MergedAnalysis.model_validate(
                {"classification": {"text_type": "章节正文"}, "sections": build_sections()}
            )
        if schema is AnalysisReport:
            self.report_calls += 1
            if self.fail_report_once and self.report_calls == 1:
                raise RuntimeError("report transient failure")
            return AnalysisReport.model_validate(build_report_payload())
        if schema is StyleSummary:
            return StyleSummary.model_validate(build_style_summary_payload("古龙风格实验"))
        if schema is PromptPack:
            return PromptPack.model_validate(build_prompt_pack_payload())
        raise AssertionError(f"unexpected schema: {schema}")


def build_pipeline(client: FakeStructuredLLMClient, checkpointer: InMemorySaver) -> StyleAnalysisPipeline:
    return StyleAnalysisPipeline(
        provider=SimpleNamespace(base_url="https://api.example.test/v1", api_key_encrypted="encrypted"),
        model_name="gpt-4.1-mini",
        style_name="古龙风格实验",
        source_filename="sample.txt",
        llm_client=client,
        checkpointer=checkpointer,
    )


@pytest.mark.asyncio
async def test_pipeline_analyzes_chunks_with_configured_max_concurrency() -> None:
    client = FakeStructuredLLMClient()
    pipeline = build_pipeline(client, InMemorySaver())

    result = await pipeline.run(
        thread_id="job-concurrency",
        cleaned_text="\n\n".join(f"段落 {index}" for index in range(10)),
        chunks=[f"chunk {index}" for index in range(10)],
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
    assert result.analysis_meta.chunk_count == 10
    assert result.analysis_report.sections[0].section == "3.1"


@pytest.mark.asyncio
async def test_pipeline_resumes_failed_report_stage_without_reanalyzing_chunks() -> None:
    checkpointer = InMemorySaver()
    client = FakeStructuredLLMClient(fail_report_once=True)
    pipeline = build_pipeline(client, checkpointer)

    kwargs = {
        "thread_id": "job-resume",
        "cleaned_text": "夜色很冷。\n\n他忽然笑了。",
        "chunks": ["chunk 0", "chunk 1", "chunk 2"],
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
    assert result.prompt_pack.system_prompt.startswith("以冷峻")
