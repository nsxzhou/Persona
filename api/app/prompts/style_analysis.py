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

## sentence_rhythm
- 

## narrative_distance
- 

## detail_anchors
- 

## dialogue_aggression
- 

## irregularity_budget
- 

## anti_ai_guardrails
- 
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
        "Voice Profile 只回答“这个作者怎么写”，不要回答“写什么题材”“要推进什么剧情”“成人强度开到什么档位”。\n\n"
        f"风格名称：{style_name}\n"
        "输出起始规则：\n"
        "- 输出必须直接从 `# Voice Profile` 开始。\n"
        "- 不要输出任何前言、任务说明、来源说明或总结。\n"
        "- 不要写“作为”开头的身份化句式。\n"
        "- 不要写“好的”“下面是”“基于你提供的报告”这类解释性开场。\n\n"
        "硬性范围限制：\n"
        "- 只允许输出 6 个二级标题：`sentence_rhythm`、`narrative_distance`、`detail_anchors`、`dialogue_aggression`、`irregularity_budget`、`anti_ai_guardrails`。\n"
        "- 不要写题材推进、成人强度、overlay 名称或剧情目标。\n"
        "- 明确排除这些控制项：`genre_mother`、`intensity_level`、`desire_overlays`、`chapter_goal`。\n"
        "- 这些 overlay 名称只能作为排除项示例，不得写进结果正文：`harem_collect`、`wife_steal`、`reverse_ntr`、`hypnosis_control`、`corruption_fall`、`dominance_capture`。\n"
        "- 即便样本里含有后宫、催眠、堕落等内容，也只能提炼成写法上的距离、节奏、细节锚点和反 AI 约束，不得把它们写成生成目标。\n\n"
        "字段要求：\n"
        "- `sentence_rhythm`：说明句长、断裂点、回勾和段落呼吸。\n"
        "- `narrative_distance`：说明叙述是否贴近主角即时感官/判断，还是偏外视角。\n"
        "- `detail_anchors`：列 3-8 个稳定出现的感官/动作锚点。\n"
        "- `dialogue_aggression`：说明对白是否抢拍、试探、压迫、戏谑、轻蔑。\n"
        "- `irregularity_budget`：说明允许的轻微不规整，不得鼓励低级错误。\n"
        "- `anti_ai_guardrails`：列出 3-8 条明确禁止的 AI 腔，例如解释腔、总结腔、模板示范腔、过度对称句式。\n\n"
        f"输出模板：\n{VOICE_PROFILE_TEMPLATE}\n\n"
        f"分析报告：\n{report_markdown}"
    )
