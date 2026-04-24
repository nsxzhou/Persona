from __future__ import annotations

from typing import Any

from app.prompts.style_analysis import SHARED_ANALYSIS_RULES as CANONICAL_SHARED_ANALYSIS_RULES
from app.services.style_analysis_prompts import (
    build_chunk_analysis_prompt,
    build_prompt_pack_prompt,
)


CLASSIFICATION: dict[str, Any] = {
    "text_type": "novel",
    "has_timestamps": False,
    "has_speaker_labels": False,
    "has_noise_markers": False,
    "uses_batch_processing": True,
    "location_indexing": "chunk",
}


def test_style_prompt_compatibility_module_reexports_canonical_rules() -> None:
    from app.services.style_analysis_prompts import SHARED_ANALYSIS_RULES

    assert SHARED_ANALYSIS_RULES == CANONICAL_SHARED_ANALYSIS_RULES


def test_build_chunk_analysis_prompt_enforces_markdown_evidence_contract() -> None:
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


def test_build_prompt_pack_prompt_requires_reusable_markdown_pack() -> None:
    prompt = build_prompt_pack_prompt(
        report_markdown="# 执行摘要\n样本文风证据。",
        style_summary_markdown="# Style Summary\n短句、强压迫。",
    )

    assert "小说写作 prompt 编排器" in prompt
    assert "全局可复用的 Markdown 风格母 prompt 包" in prompt
    assert "不要绑定具体项目剧情" in prompt
    assert "不要引入报告中没有的结论" in prompt
    assert "# Shared Style Rules" in prompt
    assert "# Style Transfer Prompt" in prompt
    assert "# Anti-Pattern Guardrails" in prompt
