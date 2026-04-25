from __future__ import annotations

from typing import Any

from app.prompts.style_analysis import PROMPT_PACK_TEMPLATE
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
    assert "输出必须直接从 `# Shared Style Rules` 开始" in prompt
    assert "# Shared Style Rules" in prompt
    assert "# Style Transfer Prompt" in prompt
    assert "# Anti-Pattern Guardrails" in prompt


def test_build_prompt_pack_prompt_enforces_desampled_abstractions() -> None:
    prompt = build_prompt_pack_prompt(
        report_markdown="# 执行摘要\n样本文风证据。",
        style_summary_markdown="# Style Summary\n穿越者内心独白强，仙侠与现代词汇混搭。",
    )

    assert "去样本化规则" in prompt
    assert "不要保留样本人物名、地名、组织名、专属设定词、事件名" in prompt
    assert "具体角色关系必须改写为角色原型" in prompt
    assert "具体冲突必须改写为冲突原型" in prompt
    assert "具体世界词必须改写为语义类别" in prompt
    assert "不要把样本主角模板、题材设定、叙事人称直接写成全局硬约束" in prompt
    assert "只有当样本证据非常明确且跨段稳定时" in prompt
    assert "优先采用的偏好" in prompt


def test_build_prompt_pack_prompt_rejects_meta_openers_and_named_few_shots() -> None:
    prompt = build_prompt_pack_prompt(
        report_markdown="# 执行摘要\n样本文风证据。",
        style_summary_markdown="# Style Summary\n对话驱动，人物差异明显。",
    )

    assert "不要输出任何前言、任务说明、来源说明或总结" in prompt
    assert "不要写“好的”“下面是”“基于你提供的报告/摘要”" in prompt
    assert "最终产物必须可单独阅读" in prompt
    assert "Few-shot Slots 只保留角色原型 + 通用示例" in prompt
    assert "不得写成样本摘录、样本改写或实名化示例" in prompt


def test_build_prompt_pack_prompt_keeps_adult_material_as_style_not_content_target() -> None:
    prompt = build_prompt_pack_prompt(
        report_markdown="# 执行摘要\n样本包含暧昧推拉和成人禁忌氛围。",
        style_summary_markdown="# Style Summary\n克制、危险吸引、留白明显。",
    )

    assert "成人相关内容只能迁移为语气、节奏、对话潜台词、镜头距离和留白方式" in prompt
    assert "不得把样本中的成人桥段、关系禁忌或擦边场景写成后续项目必须生成的内容目标" in prompt
    assert "不得要求生成露骨性描写、具体性行为、色情器官化描写、强迫、催眠/精神控制、药物控制、未成年或乱伦内容" in prompt
    assert "如需保留刺激感，只能写成成年人之间的克制暧昧、危险吸引、身份差、利益交换、误会、嫉妒或镜头外留白" in prompt


def test_prompt_pack_template_remains_fillable_skeleton() -> None:
    assert PROMPT_PACK_TEMPLATE.startswith("# Shared Style Rules")
    assert "- Rule 1:" in PROMPT_PACK_TEMPLATE
    assert "- Text:" in PROMPT_PACK_TEMPLATE
    assert "只写跨作品稳定成立的风格机制" not in PROMPT_PACK_TEMPLATE
    assert "不得写成样本摘录、样本改写或实名化示例" not in PROMPT_PACK_TEMPLATE
