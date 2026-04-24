from __future__ import annotations

import json
from typing import Any

from app.schemas.style_analysis_jobs import STYLE_ANALYSIS_REPORT_SECTIONS
from app.prompts.common import EVIDENCE_BOUNDARY_RULE, MARKDOWN_ONLY_RULE

SHARED_ANALYSIS_RULES = f"""
你必须遵守以下规则：
1. {EVIDENCE_BOUNDARY_RULE}不得编造不存在的设定、说话人或风格特征。
2. {MARKDOWN_ONLY_RULE}
3. 如果证据不足，必须在对应章节明确写出“当前样本中证据有限”。
4. 关注文本类型、索引方式、噪声、批处理条件，并在后续分析中保持一致。
5. 标题层级、章节顺序必须严格遵守要求，不要缺节，不要重排。
""".strip()


def _format_sections() -> str:
    return "\n".join(f"- {section} {title}" for section, title in STYLE_ANALYSIS_REPORT_SECTIONS)


REPORT_TEMPLATE = """
# 执行摘要
用 1-3 段总结整体文风。

# 基础判断
- 文本类型：
- 是否多说话人：
- 是否分块处理：
- 证据定位方式：
- 噪声处理：

# 风格维度
## 3.1 口头禅与常用表达
## 3.2 固定句式与节奏偏好
## 3.3 词汇选择偏好
## 3.4 句子构造习惯
## 3.5 生活经历线索
## 3.6 行业／地域词汇
## 3.7 自然化缺陷
## 3.8 写作忌口与避讳
## 3.9 比喻口味与意象库
## 3.10 思维模式与表达逻辑
## 3.11 常见场景的说话方式
## 3.12 个人价值取向与反复母题

# 附录
可选补充说明；如果没有可写“无”。
""".strip()


STYLE_SUMMARY_TEMPLATE = """
# 风格名称

# 风格定位

# 核心特征
- 

# 词汇偏好
- 

# 节奏画像
- 

# 标点画像
- 

# 意象与主题
- 

# 场景策略
## 对白
## 动作
## 环境

# 避免或少用
- 

# 生成备注
- 
""".strip()


PROMPT_PACK_TEMPLATE = """
# Shared Style Rules

# Style Transfer Prompt

# Scene Prompts
## Dialogue
## Action
## Environment

# Anti-Pattern Guardrails
- 

# Style Controls
## Tone
## Rhythm
## Evidence Anchor

# Few-shot Slots
## Slot 1
- Label:
- Type:
- Purpose:
- Text:
""".strip()


def build_chunk_analysis_prompt(
    *,
    chunk: str,
    chunk_index: int,
    classification: dict[str, Any],
    chunk_count: int,
) -> str:
    return (
        f"{SHARED_ANALYSIS_RULES}\n\n"
        "你正在执行分块分析阶段。请基于当前 chunk 输出一份 Markdown 分析片段。\n"
        "要求：保留全部 12 个风格章节，每节写 1-3 个要点；证据不足时明确写出证据有限。\n\n"
        f"输入判定：{json.dumps(classification, ensure_ascii=False)}\n"
        f"当前 chunk：{chunk_index + 1}/{chunk_count}\n"
        f"固定章节：\n{_format_sections()}\n\n"
        f"输出模板：\n{REPORT_TEMPLATE}\n\n"
        f"样本文本：\n{chunk}"
    )


def build_merge_prompt(
    *,
    chunk_analyses: list[dict[str, Any]],
    classification: dict[str, Any],
) -> str:
    return (
        f"{SHARED_ANALYSIS_RULES}\n\n"
        "你正在执行全局聚合阶段。请把多个 chunk 的 Markdown 分析合并成一份统一的 Markdown 报告草稿。\n"
        "要求：同义归并、重复证据去重、弱判断保留、多说话人差异不抹平，保持章节顺序。\n\n"
        f"输入判定：{json.dumps(classification, ensure_ascii=False)}\n"
        f"固定章节：\n{_format_sections()}\n\n"
        f"输出模板：\n{REPORT_TEMPLATE}\n\n"
        f"待合并结果：\n{json.dumps(chunk_analyses, ensure_ascii=False)}"
    )


def build_report_prompt(
    *,
    merged_analysis_markdown: str,
    classification: dict[str, Any],
) -> str:
    return (
        f"{SHARED_ANALYSIS_RULES}\n\n"
        "你正在把聚合结果整理成最终分析报告。输出必须是完整 Markdown 文档。\n\n"
        f"输入判定：{json.dumps(classification, ensure_ascii=False)}\n"
        f"输出模板：\n{REPORT_TEMPLATE}\n\n"
        f"聚合结果：\n{merged_analysis_markdown}"
    )


def build_style_summary_prompt(
    *,
    report_markdown: str,
    style_name: str,
) -> str:
    return (
        f"{SHARED_ANALYSIS_RULES}\n\n"
        "你正在从完整分析报告提炼可编辑风格摘要。输出必须是 Markdown 文档。\n"
        "不要引入报告中不存在的结论；尽量高密度、可用于后续生成。\n\n"
        f"风格名称：{style_name}\n"
        f"输出模板：\n{STYLE_SUMMARY_TEMPLATE}\n\n"
        f"分析报告：\n{report_markdown}"
    )


def build_prompt_pack_prompt(
    *,
    report_markdown: str,
    style_summary_markdown: str,
) -> str:
    return (
        "你是一位小说写作 prompt 编排器。"
        "请基于完整分析报告和当前风格摘要，生成一个全局可复用的 Markdown 风格母 prompt 包。"
        "不要绑定具体项目剧情，不要引入报告中没有的结论。\n\n"
        f"输出模板：\n{PROMPT_PACK_TEMPLATE}\n\n"
        f"分析报告：\n{report_markdown}\n\n"
        f"当前风格摘要：\n{style_summary_markdown}"
    )
