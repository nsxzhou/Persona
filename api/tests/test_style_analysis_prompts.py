from __future__ import annotations

from typing import Any

from app.prompts.style_analysis import VOICE_PROFILE_TEMPLATE
from app.services.style_analysis_prompts import (
    build_chunk_analysis_prompt,
    build_voice_profile_prompt,
)


CLASSIFICATION: dict[str, Any] = {
    "text_type": "novel",
    "has_timestamps": False,
    "has_speaker_labels": False,
    "has_noise_markers": False,
    "uses_batch_processing": True,
    "location_indexing": "chunk",
}


def test_build_chunk_analysis_prompt_keeps_markdown_evidence_contract() -> None:
    prompt = build_chunk_analysis_prompt(
        chunk="独特风格样本：ALPHA-STYLE",
        chunk_index=2,
        chunk_count=5,
        classification=CLASSIFICATION,
    )

    assert "输出必须使用中文简体 Markdown" in prompt
    assert "不要输出 JSON" in prompt
    assert "不要输出代码块" in prompt
    assert "证据优先" in prompt
    assert "当前样本中证据有限" in prompt
    assert "固定章节" in prompt
    assert "3/5" in prompt
    assert "独特风格样本：ALPHA-STYLE" in prompt


def test_build_voice_profile_prompt_requires_new_heading_and_sections() -> None:
    prompt = build_voice_profile_prompt(
        report_markdown="# 执行摘要\n样本文风证据。",
        style_name="冷白短句",
    )

    assert "生成一个可复用的 Voice Profile" in prompt
    assert "输出必须直接从 `# Voice Profile` 开始" in prompt
    assert "# Voice Profile" in prompt
    for section in (
        "## sentence_rhythm",
        "## narrative_distance",
        "## detail_anchors",
        "## dialogue_aggression",
        "## irregularity_budget",
        "## anti_ai_guardrails",
    ):
        assert section in prompt


def test_build_voice_profile_prompt_bans_story_and_nsfw_control_fields() -> None:
    prompt = build_voice_profile_prompt(
        report_markdown="# 执行摘要\n样本同时包含仙侠升级与后宫压迫。",
        style_name="冷白短句",
    )

    assert "不要写题材推进、成人强度、overlay 名称或剧情目标" in prompt
    assert "genre_mother" in prompt
    assert "intensity_level" in prompt
    assert "desire_overlays" in prompt
    assert "chapter_goal" in prompt
    assert "harem_collect" in prompt
    assert "hypnosis_control" in prompt


def test_build_voice_profile_prompt_rejects_meta_openers() -> None:
    prompt = build_voice_profile_prompt(
        report_markdown="# 执行摘要\n样本文风证据。",
        style_name="冷白短句",
    )

    assert "不要输出任何前言、任务说明、来源说明或总结" in prompt
    assert "不要写“作为”开头的身份化句式" in prompt
    assert "不要写“好的”“下面是”“基于你提供的报告”" in prompt


def test_voice_profile_template_matches_runtime_contract() -> None:
    assert VOICE_PROFILE_TEMPLATE.startswith("# Voice Profile")
    assert "## sentence_rhythm" in VOICE_PROFILE_TEMPLATE
    assert "## anti_ai_guardrails" in VOICE_PROFILE_TEMPLATE
    assert "Shared Style Rules" not in VOICE_PROFILE_TEMPLATE
