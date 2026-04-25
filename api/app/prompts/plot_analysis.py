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


STORY_ENGINE_TEMPLATE = """
# Story Engine Profile

## genre_mother
- 

## drive_axes
- 

## payoff_objects
- 

## pressure_formulas
- 

## relation_roles
- 

## scene_verbs
- 

## hook_recipes
- 

## anti_drift_guardrails
- 

## suggested_overlays
- 
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
        '"events": ["林凡出场", "遭遇宗门考核"], '
        '"advancement": "setup", '
        '"time_marker": "linear"}'
    )
    return (
        f"{SKETCH_ANALYSIS_RULES}\n\n"
        "你正在执行 Plot Lab 的分块速写阶段（sketch pass）。请基于当前 chunk 产出一份"
        "用于后续搭建全书骨架的紧凑 JSON 摘要，整份内容合计不得超过 200 个汉字。\n"
        "如果提供了邻接上下文，它们只用于补全跨边界信息，不应把纯邻接上下文中的事件重复记为当前 chunk 的独立事件。\n"
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
    overlap_before: str = "",
    overlap_after: str = "",
) -> str:
    skeleton_block = _format_skeleton_context(plot_skeleton)
    return (
        f"{SHARED_ANALYSIS_RULES}\n\n"
        "你正在执行 Plot Lab 的分块分析阶段。请基于当前 chunk 提取情节推进信息，而不是语言文风。\n"
        "要求：保留全部 12 个情节章节，每节写 1-3 个要点；优先提取事件链、关系变化、压力来源、爽点兑现和主角道德口径。\n"
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


def build_story_engine_prompt(
    *,
    report_markdown: str,
    plot_name: str,
) -> str:
    return (
        f"{SHARED_ANALYSIS_RULES}\n\n"
        "你正在从完整 Plot Lab 报告生成一个可复用的 Story Engine Profile。输出必须是 Markdown 文档。\n"
        "Story Engine 只回答“这类书靠什么推进追读”，不要写续写模板口吻，不要写旧式 Prompt Pack 分区。\n\n"
        f"情节档案名称：{plot_name}\n"
        "输出起始规则：\n"
        "- 输出必须直接从 `# Story Engine Profile` 开始。\n"
        "- 不要输出任何前言、任务说明、来源说明或总结。\n"
        "- 不要写“作为”开头的身份化句式。\n"
        "- 不要写旧 Prompt Pack 分区名或类似的约束口号。\n\n"
        "硬性结构：\n"
        "- 只允许输出 9 个二级标题：`genre_mother`、`drive_axes`、`payoff_objects`、`pressure_formulas`、`relation_roles`、`scene_verbs`、`hook_recipes`、`anti_drift_guardrails`、`suggested_overlays`。\n"
        "- `genre_mother` 必须在 `xianxia`、`urban`、`historical_power`、`infinite_flow`、`gaming` 中选一。\n"
        "- `suggested_overlays` 只输出倾向推荐，不输出执行指令；允许的 overlay 名称：`harem_collect`、`wife_steal`、`reverse_ntr`、`hypnosis_control`、`corruption_fall`、`dominance_capture`。\n\n"
        "抽象要求：\n"
        "- 明确提炼主驱动轴、兑现物、压迫公式、关系功能位、场景动作和钩子配方。\n"
        "- 不要使用旧版成人边界收束语言。\n"
        "- 可以显式识别并输出可能的 overlay 倾向，但不得把它写成完整续写脚本。\n"
        "- 不要保留样本人物名、事件名、势力名、世界专名或章节号。\n\n"
        f"输出模板：\n{STORY_ENGINE_TEMPLATE}\n\n"
        f"分析报告：\n{report_markdown}"
    )
