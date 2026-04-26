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


VOICE_PROFILE_TEMPLATE = """
# Voice Profile

## 3.1 口头禅与常用表达
- 执行规则：
- 证据摘要：

## 3.2 固定句式与节奏偏好
- 执行规则：
- 证据摘要：

## 3.3 词汇选择偏好
- 执行规则：
- 证据摘要：

## 3.4 句子构造习惯
- 执行规则：
- 证据摘要：

## 3.5 生活经历线索
- 执行规则：
- 证据摘要：

## 3.6 行业／地域词汇
- 执行规则：
- 证据摘要：

## 3.7 自然化缺陷
- 执行规则：
- 证据摘要：

## 3.8 写作忌口与避讳
- 执行规则：
- 证据摘要：

## 3.9 比喻口味与意象库
- 执行规则：
- 证据摘要：

## 3.10 思维模式与表达逻辑
- 执行规则：
- 证据摘要：

## 3.11 常见场景的说话方式
- 执行规则：
- 证据摘要：

## 3.12 个人价值取向与反复母题
- 执行规则：
- 证据摘要：
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


def build_voice_profile_prompt(
    *,
    report_markdown: str,
    style_name: str,
) -> str:
    return (
        f"{SHARED_ANALYSIS_RULES}\n\n"
        "你正在从完整分析报告生成一个可复用的 Voice Profile。输出必须是 Markdown 文档。\n"
        "Voice Profile 只回答“这个文本怎么写”，目标是提炼语句风格、节奏、词汇、对白、标点、意象和逻辑习惯。\n\n"
        f"风格名称：{style_name}\n"
        "输出起始规则：\n"
        "- 输出必须直接从 `# Voice Profile` 开始。\n"
        "- 不要输出任何前言、任务说明、来源说明或总结。\n"
        "- 不要写“作为”开头的身份化句式。\n"
        "- 不要写“好的”“下面是”“基于你提供的报告”这类解释性开场。\n\n"
        "结构要求：\n"
        "- 只允许输出 12 个二级标题，标题必须逐字使用 3.1-3.12 的中文标题，不要新增、删除或重排章节。\n"
        "- 每节使用“执行规则 + 证据摘要”的结构；先写可执行的写法规律，再用少量压缩证据说明依据。\n"
        "- 执行规则必须具体到句式、节奏、词汇、标点、对白、意象或逻辑，不要写“有画面感”“文笔细腻”这类空泛评价。\n"
        "- 证据摘要可以压缩复述，不需要穷尽列举；若分析报告证据不足，写“当前样本中证据有限”。\n"
        "- Voice Profile 必须去样本化：人物名、地名、组织名、专属设定词改写为“主角”“上位者”“亲密关系角色”“对手”“组织势力”等通用关系标签。\n\n"
        "章节写法重点：\n"
        "- 3.1：高频短语、口头禅、反复出现的语气结构。\n"
        "- 3.2：长短句比例、停顿、回勾、段落呼吸、动作链推进。\n"
        "- 3.3：口语/书面/古典/网络/行业词的混合方式和替代表达。\n"
        "- 3.4：句首、句中、句尾惯用结构，以及省略号、破折号、问号等标点习惯。\n"
        "- 3.5：可转化为风格锚点的生活经验、物件、场景或经验语境；没有则明确证据有限。\n"
        "- 3.6：行业术语、方言、俚语、网络语和地域文化词。\n"
        "- 3.7：可保留的自然化不规整，如省略、跳接、断句、轻微粗粝口语。\n"
        "- 3.8：作者明显少用或避开的表达方式，只写与文风有关的忌口。\n"
        "- 3.9：偏好的比喻路径、感官意象和象征物。\n"
        "- 3.10：观察、质疑、类比、结论、情绪转折等思维推进方式。\n"
        "- 3.11：不同场景下对白的攻击性、试探、调侃、沉默和命令方式。\n"
        "- 3.12：反复出现的价值判断、母题和叙事关注点。\n\n"
        f"输出模板：\n{VOICE_PROFILE_TEMPLATE}\n\n"
        f"分析报告：\n{report_markdown}"
    )
