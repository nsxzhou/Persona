from __future__ import annotations

import json
from typing import Any

from app.schemas.plot_analysis_jobs import PLOT_ANALYSIS_REPORT_SECTIONS

SHARED_ANALYSIS_RULES = """
你必须遵守以下规则：
1. 所有结论必须证据优先，不得编造不存在的事件链、人物关系、道德转折或推进机制。
2. 输出必须使用中文简体 Markdown，不要输出 JSON、不要输出代码块、不要输出额外解释。
3. 如果证据不足，必须在对应章节明确写出“当前样本中证据有限”。
4. 区分叙事出现顺序与可推断的真实时序；若无法确定，必须明确标注“时序不确定”。
5. 标题层级、章节顺序必须严格遵守要求，不要缺节，不要重排。
6. 报告层允许直接使用“胁迫、利用、控制、占有”等词；Prompt Pack 层需转成可执行约束，但不得洗白。
""".strip()


def _format_sections() -> str:
    return "\n".join(f"- {section} {title}" for section, title in PLOT_ANALYSIS_REPORT_SECTIONS)


PLOT_REPORT_TEMPLATE = """
# 执行摘要
用 1-3 段总结这本书真正依赖什么推进读者追读。

# 基础判断
- 叙事模式：
- 核心推进模式：
- 主角道德口径：
- 关系启动方式：
- 洗白风险等级：

# 情节维度
## 3.1 阶段划分与字数节奏
## 3.2 主爽点线与兑现节奏
## 3.3 冲突类型谱
## 3.4 主角道德与能力走向
## 3.5 关键角色引入模式
## 3.6 关系性质演变
## 3.7 爽点类型与兑现方式
## 3.8 章末钩子模式
## 3.9 反套路/颠覆点分布
## 3.10 道德灰度与下限
## 3.11 结局形状
## 3.12 标志性场景类型

# 附录
可补充证据定位、时序说明与证据不足项；如果没有可写“无”。
""".strip()


PLOT_SUMMARY_TEMPLATE = """
# 剧情定位

# 读者追读抓手
- 

# 主角道德边界
- 

# 阶段推进骨架
- 

# 关系推进公式
- 

# 压力系统
- 

# 必有场景
- 

# 生成禁区
- 
""".strip()


PLOT_PROMPT_PACK_TEMPLATE = """
# Shared Constraints
- 

# Tone Lock
- 

# Anti-Whitewash Guardrails
- 

# Outline Master Prompt

# Volume Planning Prompt

# Chapter Outline Prompt

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
        "你正在执行 Plot Lab 的分块分析阶段。请基于当前 chunk 提取情节推进信息，而不是语言文风。\n"
        "要求：保留全部 12 个情节章节，每节写 1-3 个要点；优先提取事件链、关系变化、压力来源、爽点兑现和主角道德口径。\n"
        "明确区分：1）叙事出现顺序；2）若证据充分，可推断的真实时序。\n\n"
        f"输入判定：{json.dumps(classification, ensure_ascii=False)}\n"
        f"当前 chunk：{chunk_index + 1}/{chunk_count}\n"
        f"固定章节：\n{_format_sections()}\n\n"
        f"输出模板：\n{PLOT_REPORT_TEMPLATE}\n\n"
        f"样本文本：\n{chunk}"
    )


def build_merge_prompt(
    *,
    chunk_analyses: list[dict[str, Any]],
    classification: dict[str, Any],
) -> str:
    return (
        f"{SHARED_ANALYSIS_RULES}\n\n"
        "你正在执行 Plot Lab 的全局聚合阶段。请把多个 chunk 的 Markdown 情节分析合并成一份统一的 Markdown 报告草稿。\n"
        "要求：按推进链路归并同义事件，保留叙事顺序，并在证据明确时补出真实时序；若存在倒叙/插叙/多线并行但无法完全重建，必须标注时序不确定。\n\n"
        f"输入判定：{json.dumps(classification, ensure_ascii=False)}\n"
        f"固定章节：\n{_format_sections()}\n\n"
        f"输出模板：\n{PLOT_REPORT_TEMPLATE}\n\n"
        f"待合并结果：\n{json.dumps(chunk_analyses, ensure_ascii=False)}"
    )


def build_report_prompt(
    *,
    merged_analysis_markdown: str,
    classification: dict[str, Any],
) -> str:
    return (
        f"{SHARED_ANALYSIS_RULES}\n\n"
        "你正在把聚合结果整理成最终 Plot Lab 分析报告。输出必须是完整 Markdown 文档。\n\n"
        f"输入判定：{json.dumps(classification, ensure_ascii=False)}\n"
        f"输出模板：\n{PLOT_REPORT_TEMPLATE}\n\n"
        f"聚合结果：\n{merged_analysis_markdown}"
    )


def build_plot_summary_prompt(
    *,
    report_markdown: str,
    plot_name: str,
) -> str:
    return (
        f"{SHARED_ANALYSIS_RULES}\n\n"
        "你正在从完整 Plot Lab 报告提炼可编辑的剧情摘要。输出必须是 Markdown 文档。\n"
        "不要引入报告中不存在的结论；尽量高密度、可用于后续总纲/分卷/章节细纲生成。\n\n"
        f"情节档案名称：{plot_name}\n"
        f"输出模板：\n{PLOT_SUMMARY_TEMPLATE}\n\n"
        f"分析报告：\n{report_markdown}"
    )


def build_prompt_pack_prompt(
    *,
    report_markdown: str,
    plot_summary_markdown: str,
) -> str:
    return (
        "你是一位小说情节 prompt 编排器。"
        "请基于完整 Plot Lab 分析报告和当前剧情摘要，生成一个全局可复用的 Markdown 情节母 prompt 包。"
        "输出必须覆盖 Shared Constraints、Tone Lock、Anti-Whitewash Guardrails，以及分别给总纲/分卷/章节细纲使用的子 Prompt。"
        "不要绑定具体项目剧情，不要引入报告中没有的结论。\n\n"
        f"输出模板：\n{PLOT_PROMPT_PACK_TEMPLATE}\n\n"
        f"分析报告：\n{report_markdown}\n\n"
        f"当前剧情摘要：\n{plot_summary_markdown}"
    )
