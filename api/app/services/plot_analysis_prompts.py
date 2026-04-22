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


# Sketch pass must emit a structured JSON object (for downstream aggregation),
# which is the ONE place where rule #2 of SHARED_ANALYSIS_RULES is inverted.
SKETCH_ANALYSIS_RULES = """
你必须遵守以下规则：
1. 所有结论必须证据优先，不得编造不存在的事件链、人物关系或推进机制。
2. 输出必须是一个合法的 JSON 对象，仅输出该 JSON 对象本身；不要输出 Markdown、不要输出代码块、不要输出额外解释或前后缀。
3. JSON 内部字符串必须使用中文简体；字段名称必须严格使用指定的英文字段名，不得翻译。
4. 若证据不足，宁可保留空数组或给出最小可支撑结论，也不要编造。
5. JSON 对象必须只包含指定字段，不得出现任何额外字段或注释。
""".strip()


def _format_sections() -> str:
    return "\n".join(f"- {section} {title}" for section, title in PLOT_ANALYSIS_REPORT_SECTIONS)


def _format_skeleton_context(plot_skeleton: str | None) -> str:
    """Render the optional "全书骨架" reference block shared by downstream builders.

    Returns an empty string when no skeleton is supplied so callers can unconditionally
    splice the output into their prompt template without introducing blank sections.
    """

    if plot_skeleton is None:
        return ""
    stripped = plot_skeleton.strip()
    if not stripped:
        return ""
    return (
        "## 全书骨架（参考上下文）\n"
        f"{stripped}\n\n"
        "骨架仅用于定位与上下文参考；所有结论仍须以本 chunk 证据为准，不得引用骨架外的事件。\n\n"
    )


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


PLOT_SKELETON_TEMPLATE = """
# 全书骨架

## 阶段划分（按 chunk 索引）
（例如：启动期 0-12；上升期 13-45；主高潮期 46-80；收束期 81-99。每阶段一句概括。）

## 主线推进链
（列出 5-10 个关键设伏 @chunkA → 兑现 @chunkB 对，一句话描述）

## 爽点兑现节奏
（列出密集区 / 转折区对应的 chunk 范围）

## 角色登场 & 主角能力阶梯
（主角: 初始 → chunk X 大事件 → chunk Y 大事件 …；关键配角逐条）

## 时间线结构
（线性 / 含倒叙插叙——若插叙，指出对应 chunk 范围）

## 结局形状线索
（≤ 3 句总括结局形态）

## 证据不足项
（若任一节证据不足，列于此；否则写“无”）
""".strip()


def build_sketch_prompt(
    *,
    chunk: str,
    chunk_index: int,
    chunk_count: int,
    classification: dict[str, Any],
) -> str:
    """Prompt for the per-chunk "sketch" pre-pass that feeds skeleton reduction.

    Output must be a compact JSON object matching ``PlotChunkSketch`` exactly; this is
    the single place in this module where we deliberately invert the shared Markdown
    rule. Builder-local ``SKETCH_ANALYSIS_RULES`` allows JSON and forbids Markdown.
    """

    example_json = (
        '{"chunk_index": 0, "chunk_count": 100, '
        '"characters_present": ["林凡", "宗主"], '
        '"events": ["林凡出场", "遭遇宗门考核"], '
        '"advancement": "setup", '
        '"time_marker": "linear"}'
    )
    return (
        f"{SKETCH_ANALYSIS_RULES}\n\n"
        "你正在执行 Plot Lab 的分块速写阶段（sketch pass）。请基于当前 chunk 产出一份"
        "用于后续搭建全书骨架的紧凑 JSON 摘要，整份内容合计不得超过 200 个汉字。\n"
        "字段定义（字段名必须保持英文原样，不要翻译）：\n"
        "- `chunk_index`：当前 chunk 的零基索引，必须等于传入值。\n"
        "- `chunk_count`：本次任务的 chunk 总数，必须等于传入值。\n"
        "- `characters_present`：本 chunk 中直接出场或被点名的主要角色列表，仅保留主要行动者，最多 10 个。\n"
        "- `events`：本 chunk 的关键事件点，按叙事顺序排列，每条 ≤ 40 个汉字。\n"
        "- `advancement`：本 chunk 在全书推进中的角色，取值必须是以下之一："
        "`setup`（铺垫）、`payoff`（兑现）、`transition`（过渡）、`interlude`（插曲）。\n"
        "- `time_marker`：本 chunk 的时间线标记，取值必须是以下之一："
        "`linear`（线性推进）、`flashback`（倒叙或插叙）、`unclear`（暂无法判定）。\n"
        "JSON 对象只能包含上述 6 个字段，不得出现任何其他字段。\n\n"
        f"输入判定：{json.dumps(classification, ensure_ascii=False)}\n"
        f"当前 chunk：{chunk_index + 1}/{chunk_count}"
        f"（chunk_index={chunk_index}, chunk_count={chunk_count}）\n\n"
        "输出形状示例（仅用于说明 JSON 字段形状，不要照搬其中内容）：\n"
        f"{example_json}\n\n"
        "请仅输出符合上述要求的 JSON 对象，不要输出任何其他字符。\n\n"
        f"样本文本：\n{chunk}"
    )


def build_skeleton_reduce_prompt(
    *,
    sketches: list[dict[str, Any]],
    classification: dict[str, Any],
    chunk_count: int,
) -> str:
    """Prompt reducing per-chunk sketches into the final ``plot-skeleton.md`` overview.

    This reducer also accepts sub-skeleton objects produced by
    ``build_skeleton_group_reduce_prompt`` (hierarchical fallback), so the prompt is
    explicitly tolerant of either shape in the ``sketches`` payload.
    """

    return (
        f"{SHARED_ANALYSIS_RULES}\n\n"
        "你正在执行 Plot Lab 的全书骨架聚合阶段。请基于已按 `chunk_index` 升序排列的分块速写（sketches），"
        "压缩输出一份紧凑的全书骨架 Markdown，用于后续 chunk 级深入分析提供全局上下文。\n"
        "整份骨架合计不得超过约 2500 tokens；章节、层级与顺序必须严格沿用下方输出模板。\n"
        "若证据不足，宁可在“证据不足项”中声明，不要凭空臆断；每一阶段、每一推进链条都必须"
        "能够在输入的 sketches 中找到对应证据。\n"
        "请尽量用 chunk 索引（例如 `@chunk42`、`chunk 12-45`）来锚定阶段、设伏、兑现和时间线。\n"
        "输入 `sketches` 既可能是分块速写 JSON，也可能是由子骨架聚合阶段产生的 Markdown 片段对象；"
        "请对两种形状都做兼容处理。\n\n"
        f"输入判定：{json.dumps(classification, ensure_ascii=False)}\n"
        f"chunk 总数：{chunk_count}\n\n"
        f"输出模板：\n{PLOT_SKELETON_TEMPLATE}\n\n"
        f"分块速写列表（已按 chunk_index 升序排列）：\n"
        f"{json.dumps(sketches, ensure_ascii=False)}"
    )


def build_skeleton_group_reduce_prompt(
    *,
    group_sketches: list[dict[str, Any]],
    group_index: int,
    group_count: int,
    classification: dict[str, Any],
) -> str:
    """Hierarchical fallback: reduce a subset of sketches into a sub-skeleton markdown.

    Used when the full sketch payload would exceed the aggregate reducer's context
    budget (~80K tokens). Output shape mirrors ``PLOT_SKELETON_TEMPLATE`` but is scoped
    to the sketch range in this group — downstream aggregation is then performed by
    ``build_skeleton_reduce_prompt`` over the generated sub-skeletons.
    """

    return (
        f"{SHARED_ANALYSIS_RULES}\n\n"
        "你正在执行 Plot Lab 的骨架分组归并阶段（group reduce）。当 chunk 总数过大时，"
        "分块速写会被切成若干组先分别聚合成子骨架（sub-skeleton），再由最终聚合步骤合并成完整骨架。\n"
        f"当前是 group {group_index + 1}/{group_count} 的子骨架。仅基于传入的 sketch 范围，"
        "不要推断外部 chunk；所有 chunk 索引引用都必须出现在传入 sketches 中。\n"
        "子骨架必须沿用与最终骨架相同的章节结构与层级，在各条目中明确标注所覆盖的 chunk 索引范围，"
        "并在当前 group 范围内证据不足时，将具体条目列入“证据不足项”，不要凭空臆断。\n\n"
        f"输入判定：{json.dumps(classification, ensure_ascii=False)}\n"
        f"当前 group：{group_index + 1}/{group_count}\n\n"
        f"输出模板：\n{PLOT_SKELETON_TEMPLATE}\n\n"
        "本 group 分块速写列表（已按 chunk_index 升序排列）：\n"
        f"{json.dumps(group_sketches, ensure_ascii=False)}"
    )


def build_chunk_analysis_prompt(
    *,
    chunk: str,
    chunk_index: int,
    classification: dict[str, Any],
    chunk_count: int,
    plot_skeleton: str | None = None,
) -> str:
    skeleton_block = _format_skeleton_context(plot_skeleton)
    return (
        f"{SHARED_ANALYSIS_RULES}\n\n"
        "你正在执行 Plot Lab 的分块分析阶段。请基于当前 chunk 提取情节推进信息，而不是语言文风。\n"
        "要求：保留全部 12 个情节章节，每节写 1-3 个要点；优先提取事件链、关系变化、压力来源、爽点兑现和主角道德口径。\n"
        "明确区分：1）叙事出现顺序；2）若证据充分，可推断的真实时序。\n\n"
        f"输入判定：{json.dumps(classification, ensure_ascii=False)}\n"
        f"当前 chunk：{chunk_index + 1}/{chunk_count}\n"
        f"固定章节：\n{_format_sections()}\n\n"
        f"输出模板：\n{PLOT_REPORT_TEMPLATE}\n\n"
        f"{skeleton_block}"
        f"样本文本：\n{chunk}"
    )


def build_merge_prompt(
    *,
    chunk_analyses: list[dict[str, Any]],
    classification: dict[str, Any],
    plot_skeleton: str | None = None,
) -> str:
    skeleton_block = _format_skeleton_context(plot_skeleton)
    return (
        f"{SHARED_ANALYSIS_RULES}\n\n"
        "你正在执行 Plot Lab 的全局聚合阶段。请把多个 chunk 的 Markdown 情节分析合并成一份统一的 Markdown 报告草稿。\n"
        "要求：按推进链路归并同义事件，保留叙事顺序，并在证据明确时补出真实时序；若存在倒叙/插叙/多线并行但无法完全重建，必须标注时序不确定。\n\n"
        f"输入判定：{json.dumps(classification, ensure_ascii=False)}\n"
        f"固定章节：\n{_format_sections()}\n\n"
        f"输出模板：\n{PLOT_REPORT_TEMPLATE}\n\n"
        f"{skeleton_block}"
        f"待合并结果：\n{json.dumps(chunk_analyses, ensure_ascii=False)}"
    )


def build_report_prompt(
    *,
    merged_analysis_markdown: str,
    classification: dict[str, Any],
    plot_skeleton: str | None = None,
) -> str:
    skeleton_block = _format_skeleton_context(plot_skeleton)
    extra_hint = ""
    if skeleton_block:
        extra_hint = (
            "在生成 3.1 阶段划分、3.2 主爽点线兑现节奏、3.11 结局形状 时应优先参考"
            "骨架的阶段与节奏判断。\n\n"
        )
    return (
        f"{SHARED_ANALYSIS_RULES}\n\n"
        "你正在把聚合结果整理成最终 Plot Lab 分析报告。输出必须是完整 Markdown 文档。\n\n"
        f"输入判定：{json.dumps(classification, ensure_ascii=False)}\n"
        f"输出模板：\n{PLOT_REPORT_TEMPLATE}\n\n"
        f"{skeleton_block}"
        f"{extra_hint}"
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
        "请基于完整 Plot Lab 分析报告和当前剧情摘要，生成一个全局可复用、可脱离原始样本单独注入的 Markdown 情节 prompt 包。"
        "输出必须覆盖 Shared Constraints、Tone Lock、Anti-Whitewash Guardrails，以及分别给总纲/分卷/章节细纲使用的子 Prompt。"
        "不要引入报告中没有的结论。\n\n"
        "输出起始规则：\n"
        "- 输出必须直接从 `# Shared Constraints` 开始。\n"
        "- 不要输出任何前言、任务说明、来源说明或总结。\n"
        "- 不要写“作为”开头的身份化句式。\n"
        "- 不要写“好的”“下面是”“基于你提供的报告/摘要”“作为……我将……”这类解释性或身份化开场。\n"
        "- 最终产物必须可单独阅读，不得依赖“分析报告”这一上文存在。\n\n"
        "去样本化规则：\n"
        "- 不要绑定具体项目剧情，不要保留样本人物名、地名、势力名、事件名、世界观专属名词。\n"
        "- 人物名必须改写为角色原型，例如：师门权威、高位女性角色、异族继承者、竞争型反派、指导型强者。\n"
        "- 专属资源必须改写为资源原型，例如：核心稀缺资源、身份逆转筹码、境界突破媒介、血脉级利益。\n"
        "- 专属事件必须改写为冲突原型，例如：胁迫性绑定、被迫接受的契约、资源争夺引发的反转、由信息差触发的控制关系。\n"
        "- 禁止保留章节号、chunk 编号、样本专名、原作特有固有名词。\n"
        "- 整份 prompt pack 都必须使用可迁移、可复用的抽象表达，尤其是 Anti-Whitewash Guardrails 与 Few-shot Slots。\n\n"
        "结构规则：\n"
        "- Shared Constraints 只保留跨项目可复用的叙事约束，不出现具体人物或样本事件。\n"
        "- Tone Lock 只描述叙事视角、主角逻辑、关系基调、爽点核心，不指向具体样本角色。\n"
        "- Anti-Whitewash Guardrails 只写什么关系或行为不能被浪漫化或洗白，不写样本中的具体人物、师徒关系或事件名。\n"
        "- Outline Master Prompt、Volume Planning Prompt、Chapter Outline Prompt 必须写成适用于任意项目上下文的子模板，不得默认某个既有世界观。\n"
        "- Few-shot Slots 保留抽象示例，不得写成样本摘录或样本改写。\n\n"
        "Few-shot 规则：\n"
        "- Few-shot 只允许使用原型词与显式槽位。\n"
        "- 允许的原型词示例：高位角色、反派、关键关系对象、宗门权威、核心资源、绑定关系、突破机会。\n"
        "- 允许的显式槽位示例：`[角色A]`、`[高位角色B]`、`[资源C]`、`[场景D]`、`[弱点E]`。\n"
        "- 禁止出现原样本人物名、原样本事件名、原样本世界观专属名词，以及只有读过报告才看得懂的隐含指代。\n\n"
        f"输出模板：\n{PLOT_PROMPT_PACK_TEMPLATE}\n\n"
        f"分析报告：\n{report_markdown}\n\n"
        f"当前剧情摘要：\n{plot_summary_markdown}"
    )
