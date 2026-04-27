from __future__ import annotations

import json
from typing import Any

from app.schemas.plot_analysis_jobs import PLOT_ANALYSIS_REPORT_SECTIONS
from app.prompts.common import EVIDENCE_BOUNDARY_RULE, JSON_ONLY_RULE, MARKDOWN_ONLY_RULE

SHARED_ANALYSIS_RULES = f"""
你必须遵守以下规则：
1. {EVIDENCE_BOUNDARY_RULE}不得编造不存在的事件链、人物关系、道德转折或推进机制。
2. {MARKDOWN_ONLY_RULE}
3. 如果证据不足，必须在对应章节明确写出“当前样本中证据有限”。
4. 区分叙事出现顺序与可推断的真实时序；若无法确定，必须明确标注“时序不确定”。
5. 标题层级、章节顺序必须严格遵守要求，不要缺节，不要重排。
6. 报告层允许直接使用“胁迫、利用、控制、占有”等词；Prompt Pack 层需转成可执行约束，但不得洗白。
7. 分析必须追踪“核心DNA、角色欲望、世界断层线、章节悬念单元、伏笔三步法、认知颠覆”的证据，但不得把样本外剧情补成完整小说。
""".strip()


# Sketch pass must emit a structured JSON object (for downstream aggregation),
# which is the ONE place where rule #2 of SHARED_ANALYSIS_RULES is inverted.
SKETCH_ANALYSIS_RULES = f"""
你必须遵守以下规则：
1. {EVIDENCE_BOUNDARY_RULE}不得编造不存在的事件链、人物关系或推进机制。
2. {JSON_ONLY_RULE}
3. JSON 内部字符串必须使用中文简体；字段名称必须严格使用指定的英文字段名，不得翻译。
4. 若证据不足，宁可保留空数组或给出最小可支撑结论，也不要编造。
5. JSON 对象必须只包含指定字段，不得出现任何额外字段或注释。
""".strip()


def _format_sections() -> str:
    return "\n".join(f"- {section} {title}" for section, title in PLOT_ANALYSIS_REPORT_SECTIONS)


def _format_skeleton_context(plot_skeleton: str | None) -> str:
    """Render the optional sample plot skeleton reference block shared by downstream builders.

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


def _format_plot_chunk_input(
    *,
    chunk: str,
    overlap_before: str,
    overlap_after: str,
) -> str:
    sections = ["主分析文本（当前 chunk，结论优先以此为准）:\n" + chunk]
    if overlap_before.strip():
        sections.append("前邻接上下文（仅用于跨边界补全）:\n" + overlap_before)
    if overlap_after.strip():
        sections.append("后邻接上下文（仅用于跨边界补全）:\n" + overlap_after)
    return "\n\n".join(sections)


PLOT_REPORT_TEMPLATE = """
# 执行摘要
用 1-3 段总结上传样本真正依赖什么情节机制推进读者追读；只分析上传样本，不推断完整小说。

# 基础判断
- 样本覆盖范围：
- 样本是否包含开篇：
- 样本是否包含高潮：
- 样本是否包含结尾：
- 核心推进模式：

# 情节分析
## 2.5.1 主线剧情分析
## 2.5.2 支线剧情分析
## 2.5.3 细纲
## 2.5.4 场景纲
## 2.5.5 爽点
## 2.5.6 节奏

# 附录
写明当前样本未覆盖、证据不足或时序不确定的部分；如果没有可写“无”。
""".strip()


STORY_ENGINE_TEMPLATE = """
# Plot Writing Guide

## Core Plot Formula
- 

## Chapter Progression Loop
- 

## Scene Construction Rules
- 

## Setup and Payoff Rules
- 

## Payoff and Tension Rhythm
- 

## Side Plot Usage
- 

## Hook Recipes
- 

## Anti-Drift Rules
- 
""".strip()


PLOT_SKELETON_TEMPLATE = """
# 全书骨架

## 样本覆盖范围
（按 chunk 索引说明上传样本覆盖了开篇/发展/高潮/结尾中的哪些部分；未覆盖必须写明。）

## 主线推进链
（列出样本内可证据支持的关键推进链；用 @chunkA -> @chunkB 标注设伏与兑现。）

## 支线线索
（列出样本内支线、对照线、关系线，说明如何回流或映照主线。）

## 场景账本
（按 chunk 范围概括关键场景最小单元：地点/人物/事件/变化点。）

## 爽点与钩子
（列出样本内爽点、虐点、章末钩子和半兑现位置。）

## 节奏曲线
（说明张弛、压迫、反击、过渡、密集兑现的分布。）

## 证据不足项
（未覆盖开篇、高潮或结尾时必须列出；否则写“无”。）
""".strip()


def build_sketch_prompt(
    *,
    chunk: str,
    chunk_index: int,
    chunk_count: int,
    classification: dict[str, Any],
    overlap_before: str = "",
    overlap_after: str = "",
) -> str:
    """Prompt for the per-chunk "sketch" pre-pass that feeds skeleton reduction.

    Output must be a compact JSON object matching ``PlotChunkSketch`` exactly; this is
    the single place in this module where we deliberately invert the shared Markdown
    rule. Builder-local ``SKETCH_ANALYSIS_RULES`` allows JSON and forbids Markdown.
    """

    example_json = (
        '{"chunk_index": 0, "chunk_count": 100, '
        '"characters_present": ["林凡", "宗主"], '
        '"scene_units": ["宗门大比现场：林凡被宗主点名参加考核，局面从旁观转为被迫应战"], '
        '"main_events": ["林凡遭遇宗门考核"], '
        '"side_threads": ["同门观望形成压力"], '
        '"payoff_points": ["林凡当场展示能力"], '
        '"tension_points": ["宗门权威压迫"], '
        '"hooks": ["考核结果未公布"], '
        '"setup_payoff_links": ["前置轻视 -> 当场反击"], '
        '"pacing_shift": "压迫转入反击", '
        '"time_marker": "linear", '
        '"sample_coverage": ["development_seen", "partial_fragment"]}'
    )
    return (
        f"{SKETCH_ANALYSIS_RULES}\n\n"
        "你正在执行 Plot Lab 的分块速写阶段（sketch pass）。请基于当前 chunk 产出一份"
        "用于后续搭建样本情节骨架的紧凑 JSON 账本，整份内容合计不得超过 350 个汉字。\n"
        "只分析上传样本，不得推断完整小说；样本未覆盖开篇、高潮或结尾时，只能在 `sample_coverage` 中标注片段状态。\n"
        "只记录当前 chunk 的直接证据：当前 chunk 没有发生、没有出场、没有明确点名的内容，不得写入任何事件、场景或人物字段。\n"
        "请在已有字段中压缩记录可见的核心DNA、角色欲望、世界断层线、伏笔三步法或认知颠覆信号；没有直接证据时不得补写。\n"
        "如果提供了邻接上下文，它们只用于补全跨边界信息；邻接上下文不能覆盖当前 chunk 的事件归属，不应把纯邻接上下文中的事件重复记为当前 chunk 的独立事件。\n"
        "字段定义（字段名必须保持英文原样，不要翻译）：\n"
        "- `chunk_index`：当前 chunk 的零基索引，必须等于传入值。\n"
        "- `chunk_count`：本次任务的 chunk 总数，必须等于传入值。\n"
        "- `characters_present`：本 chunk 中直接出场或被点名的主要角色列表，仅保留主要行动者，最多 10 个。\n"
        "- `scene_units`：关键场景最小叙事单元，每条写清地点/人物/事件/变化点，最多 6 条。\n"
        "- `main_events`：本 chunk 直接支撑主线推进的事件，最多 6 条。\n"
        "- `side_threads`：支线、对照线、关系线或次要冲突，最多 6 条；没有则空数组。\n"
        "- `payoff_points`：爽点、高光、反击、揭示、阶段性兑现，最多 6 条。\n"
        "- `tension_points`：压迫、虐点、威胁、代价、误判或阻碍，最多 6 条。\n"
        "- `hooks`：章末/场景末制造追读的问题、威胁、诱惑或选择，最多 6 条。\n"
        "- `setup_payoff_links`：样本内可见的“铺垫 -> 兑现”链条，最多 6 条；只写当前样本能证明的链条。\n"
        "- `pacing_shift`：用一句话说明本 chunk 的节奏变化，例如“压迫转入反击”。\n"
        "- `time_marker`：本 chunk 的时间线标记，取值必须是以下之一："
        "`linear`（线性推进）、`flashback`（倒叙或插叙）、`unclear`（暂无法判定）。\n"
        "- `sample_coverage`：本 chunk 直接覆盖的样本阶段信号，取值只能来自 "
        "`opening_seen`、`development_seen`、`climax_seen`、`ending_seen`、`partial_fragment`、`coverage_unclear`。\n"
        "JSON 对象只能包含上述 12 个字段，不得出现任何其他字段。\n\n"
        f"输入判定：{json.dumps(classification, ensure_ascii=False)}\n"
        f"当前 chunk：{chunk_index + 1}/{chunk_count}"
        f"（chunk_index={chunk_index}, chunk_count={chunk_count}）\n\n"
        "输出形状示例（仅用于说明 JSON 字段形状，不要照搬其中内容）：\n"
        f"{example_json}\n\n"
        "请仅输出符合上述要求的 JSON 对象，不要输出任何其他字符。\n\n"
        f"{_format_plot_chunk_input(chunk=chunk, overlap_before=overlap_before, overlap_after=overlap_after)}"
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
        "你正在执行 Plot Lab 的样本骨架聚合阶段。请基于已按 `chunk_index` 升序排列的分块速写（sketches），"
        "压缩输出一份紧凑的样本情节骨架 Markdown，用于最终 2.5 分析报告提供上下文。\n"
        "整份骨架合计不得超过约 2500 tokens；章节、层级与顺序必须严格沿用下方输出模板。\n"
        "只分析上传样本，不得推断完整小说；未覆盖开篇、高潮或结尾时必须写入“证据不足项”。\n"
        "若证据不足，宁可在“证据不足项”中声明，不要凭空臆断；每一阶段、每一推进链条都必须"
        "能够在输入的 sketches 中找到对应证据。\n"
        "请尽量用 chunk 索引（例如 `@chunk42`、`chunk 12-45`）来锚定阶段、设伏、兑现和时间线。\n"
        "样本覆盖范围必须解释为什么能判断这些阶段信号；不要补写样本外剧情。\n"
        "主线推进链请优先写成“设伏 @chunkX -> 兑现 @chunkY”的可追踪链条；无法配对则写当前样本中证据有限。\n"
        "请显式提炼样本内可见的核心DNA雏形、角色表层目标/深层渴望/灵魂需求线索、世界断层线、悬念单元边界、伏笔三步法证据和认知颠覆点；证据不足时写入“证据不足项”。\n"
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
        "只分析上传样本，不得推断完整小说；主线推进链优先写成“设伏 @chunkX -> 兑现 @chunkY”。\n\n"
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
    overlap_before: str = "",
    overlap_after: str = "",
) -> str:
    skeleton_block = _format_skeleton_context(plot_skeleton)
    return (
        f"{SHARED_ANALYSIS_RULES}\n\n"
        "你正在执行 Plot Lab 的分块分析阶段。请基于当前 chunk 提取情节推进信息，而不是语言文风。\n"
        "要求：保留全部 12 个情节章节，每节写 1-3 个要点；每个要点采用“推进规律 + 证据摘要”的结构，先写这一段呈现出的情节机制，再压缩说明依据。\n"
        "优先提取事件链、关系变化、压力来源、爽点兑现和主角道德口径；不要只写事件复述，也不要写成抽象读后感。\n"
        "额外追踪：这一段如何体现核心DNA、角色欲望三角、世界断层线、悬念单元推进、伏笔埋设/强化/回收、认知颠覆；没有证据就明确写证据有限。\n"
        "如果提供了邻接上下文，它们只用于跨边界补全；不要把纯邻接上下文中的事件重复记为当前 chunk 的独立事件。\n"
        "明确区分：1）叙事出现顺序；2）若证据充分，可推断的真实时序。\n\n"
        f"输入判定：{json.dumps(classification, ensure_ascii=False)}\n"
        f"当前 chunk：{chunk_index + 1}/{chunk_count}\n"
        f"固定章节：\n{_format_sections()}\n\n"
        f"输出模板：\n{PLOT_REPORT_TEMPLATE}\n\n"
        f"{skeleton_block}"
        f"{_format_plot_chunk_input(chunk=chunk, overlap_before=overlap_before, overlap_after=overlap_after)}"
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
        "要求：按推进链路归并同义事件，保留叙事顺序，并在证据明确时补出真实时序；若存在倒叙/插叙/多线并行但无法完全重建，必须标注时序不确定。\n"
        "合并时保留“推进规律 + 证据摘要”的表达方式；重复证据归并，弱证据保留证据有限标记。\n"
        "必须把样本里的核心公式、角色欲望驱动、世界压力断层、章节悬念单元、伏笔三步法与认知颠覆整理成可复用模式，不要只拼接事件摘要。\n\n"
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
    return (
        f"{SHARED_ANALYSIS_RULES}\n\n"
        "你正在把聚合结果整理成最终 Plot Lab 分析报告。输出必须是完整 Markdown 文档。\n\n"
        "只分析上传样本，不得推断完整小说。样本未覆盖开篇、高潮或结尾时，必须在对应位置写“当前样本未覆盖/证据不足”。\n"
        "报告采用 2.5 结构，用于审阅情节写法；\n\n"
        "最终报告必须能支撑下一步生成 Plot Writing Guide：请在各节里保留可复用的写作机制，尤其是核心DNA公式、章节推进循环、场景压力结构、设伏兑现节奏与反漂移边界。\n\n"
        f"输入判定：{json.dumps(classification, ensure_ascii=False)}\n"
        f"输出模板：\n{PLOT_REPORT_TEMPLATE}\n\n"
        f"{skeleton_block}"
        f"聚合结果：\n{merged_analysis_markdown}"
    )


def build_story_engine_prompt(
    *,
    report_markdown: str,
    plot_name: str,
) -> str:
    return (
        f"{SHARED_ANALYSIS_RULES}\n\n"
        "你正在从完整 Plot Lab 报告生成一个可复用的 Plot Writing Guide。输出必须是 Markdown 文档。\n"
        "Plot Writing Guide 的目标是说明如何写小说剧情，而不是复述分析报告或样本剧情。\n\n"
        f"情节档案名称：{plot_name}\n"
        "输出起始规则：\n"
        "- 输出必须直接从 `# Plot Writing Guide` 开始。\n"
        "- 不要输出任何前言、任务说明、来源说明或总结。\n"
        "- 不要写“作为”开头的身份化句式。\n"
        "- 不要写旧 Prompt Pack 分区名或类似的约束口号。\n\n"
        "硬性结构：\n"
        "- 只允许输出 8 个二级标题：`Core Plot Formula`、`Chapter Progression Loop`、`Scene Construction Rules`、`Setup and Payoff Rules`、`Payoff and Tension Rhythm`、`Side Plot Usage`、`Hook Recipes`、`Anti-Drift Rules`。\n"
        "- 每节必须写成可执行写作规则，使用短 bullet，不要写分析口吻。\n\n"
        "抽象要求：\n"
        "- Core Plot Formula 必须提炼为类似“当[主角+身份]遭遇[核心事件]，必须[关键行动]，否则[灾难后果]；与此同时，[隐藏危机]发酵”的可迁移公式，但不得复用样本专名。\n"
        "- Chapter Progression Loop 必须说明 3-5 章悬念单元如何推进，如何安排认知过山车和阶段性兑现。\n"
        "- Scene Construction Rules 必须说明场景如何从欲望/压力入手，如何让角色目标、世界断层线和即时阻碍同时在场。\n"
        "- Setup and Payoff Rules 必须显式使用伏笔三步法：埋设 -> 强化 -> 回收。\n"
        "- Payoff and Tension Rhythm 必须说明压制、反击、虚假胜利、反噬、灵魂黑夜或代价显现如何形成节奏。\n"
        "- Hook Recipes 必须给出章末钩子的类型：新压力、关系变化、资源诱惑、信息差、认知颠覆或阶段性兑现。\n"
        "- 如何写小说剧情：如何制造冲突、推进章节、构造场景、埋伏笔、兑现爽点、使用支线和写章末钩子。\n"
        "- 不要复述分析报告，不要列样本剧情摘要。\n"
        "- 禁止保留样本人物名、地名、势力名、事件名、世界专名或章节号。\n"
        "- Anti-Drift Rules 必须防止输出变成世界观说明、剧情摘要或空泛分析。\n\n"
        f"输出模板：\n{STORY_ENGINE_TEMPLATE}\n\n"
        f"分析报告：\n{report_markdown}"
    )
