from __future__ import annotations

import json
from typing import Any

import pytest

from app.services.plot_analysis_prompts import (
    build_chunk_analysis_prompt,
    build_merge_prompt,
    build_prompt_pack_prompt,
    build_report_prompt,
    build_skeleton_group_reduce_prompt,
    build_skeleton_reduce_prompt,
    build_sketch_prompt,
)


CLASSIFICATION: dict[str, Any] = {
    "text_type": "novel",
    "has_timestamps": False,
    "has_speaker_labels": False,
    "has_noise_markers": False,
    "uses_batch_processing": True,
    "location_indexing": "chunk",
}

_SKELETON_HEADER = "## 全书骨架（参考上下文）"
_SKELETON_CAVEAT = "骨架仅用于定位与上下文参考；所有结论仍须以本 chunk 证据为准，不得引用骨架外的事件。"
_SAMPLE_SKELETON = (
    "# 全书骨架\n"
    "## 阶段划分（按 chunk 索引）\n"
    "启动期 0-1；上升期 2-3"
)
_REPORT_MARKDOWN = "# 执行摘要\n- 李青阳利用信息差胁迫主角。\n- 玄女在修行名义下被迫接受绑定。\n- 龙女接受婚约作为利弊权衡。\n- 圣祖精血成为身份逆转筹码。"
_PLOT_SUMMARY_MARKDOWN = (
    "# 剧情定位\n"
    "- 主角围绕宗门权力与稀缺资源制造冲突。\n"
    "\n"
    "# 关系推进公式\n"
    "- 师徒胁迫、婚约控制、失身交易、精血争夺。"
)


# --------------------------------------------------------------------------- #
#  Sketch prompt                                                              #
# --------------------------------------------------------------------------- #


def test_build_sketch_prompt_contains_required_json_fields_and_enums() -> None:
    prompt = build_sketch_prompt(
        chunk="示例段落：主角在宗门大比现场出场。",
        chunk_index=0,
        chunk_count=100,
        classification=CLASSIFICATION,
    )

    # All required JSON field names must appear
    for field in (
        "chunk_index",
        "chunk_count",
        "characters_present",
        "events",
        "advancement",
        "time_marker",
    ):
        assert field in prompt

    # Enum values for `advancement` and `time_marker`
    for value in ("setup", "payoff", "transition", "interlude"):
        assert value in prompt
    for value in ("linear", "flashback", "unclear"):
        assert value in prompt


def test_build_sketch_prompt_uses_singular_time_marker() -> None:
    prompt = build_sketch_prompt(
        chunk="片段",
        chunk_index=0,
        chunk_count=1,
        classification=CLASSIFICATION,
    )
    # Guard against accidentally pluralising the schema field name
    assert "time_markers" not in prompt


def test_build_sketch_prompt_allows_json_output_and_forbids_markdown() -> None:
    prompt = build_sketch_prompt(
        chunk="片段",
        chunk_index=0,
        chunk_count=1,
        classification=CLASSIFICATION,
    )

    # Local rules explicitly allow JSON and forbid Markdown (inverts SHARED rule #2)
    assert "合法的 JSON 对象" in prompt
    assert "不要输出 Markdown" in prompt
    # Must NOT carry the shared "输出必须使用中文简体 Markdown" clause
    assert "输出必须使用中文简体 Markdown" not in prompt


def test_build_sketch_prompt_exposes_chunk_position_and_sample_text() -> None:
    prompt = build_sketch_prompt(
        chunk="独特片段标记：ALPHA-TOKEN",
        chunk_index=5,
        chunk_count=42,
        classification=CLASSIFICATION,
    )

    # Human-readable 1-based position AND raw indices must be visible to the model
    assert "6/42" in prompt
    assert "chunk_index=5" in prompt
    assert "chunk_count=42" in prompt
    # The chunk text must be included verbatim
    assert "独特片段标记：ALPHA-TOKEN" in prompt


def test_build_sketch_prompt_separates_primary_text_from_neighbor_context() -> None:
    prompt = build_sketch_prompt(
        chunk="主正文片段",
        chunk_index=1,
        chunk_count=3,
        classification=CLASSIFICATION,
        overlap_before="前文线索",
        overlap_after="后文线索",
    )

    assert "主分析文本（当前 chunk，结论优先以此为准）" in prompt
    assert "前邻接上下文（仅用于跨边界补全）" in prompt
    assert "后邻接上下文（仅用于跨边界补全）" in prompt
    assert "前文线索" in prompt
    assert "后文线索" in prompt


def test_build_sketch_prompt_enforces_compactness_constraints() -> None:
    prompt = build_sketch_prompt(
        chunk="片段",
        chunk_index=0,
        chunk_count=1,
        classification=CLASSIFICATION,
    )

    # 200-word ceiling on the whole sketch, 40-char ceiling per event, 10 character cap
    assert "200 个汉字" in prompt
    assert "40 个汉字" in prompt
    assert "最多 10 个" in prompt


def test_build_sketch_prompt_includes_shape_example() -> None:
    prompt = build_sketch_prompt(
        chunk="片段",
        chunk_index=0,
        chunk_count=1,
        classification=CLASSIFICATION,
    )

    # The expected JSON shape example keeps the model aligned with PlotChunkSketch
    assert '"chunk_index": 0' in prompt
    assert '"advancement": "setup"' in prompt
    assert '"time_marker": "linear"' in prompt


# --------------------------------------------------------------------------- #
#  Skeleton reduce prompt                                                     #
# --------------------------------------------------------------------------- #


SKETCHES: list[dict[str, Any]] = [
    {
        "chunk_index": 0,
        "chunk_count": 2,
        "characters_present": ["主角"],
        "events": ["开场展示能力"],
        "advancement": "setup",
        "time_marker": "linear",
    },
    {
        "chunk_index": 1,
        "chunk_count": 2,
        "characters_present": ["主角", "配角"],
        "events": ["遭遇冲突", "初次兑现"],
        "advancement": "payoff",
        "time_marker": "linear",
    },
]


@pytest.mark.parametrize(
    "header",
    [
        "# 全书骨架",
        "## 阶段划分（按 chunk 索引）",
        "## 主线推进链",
        "## 爽点兑现节奏",
        "## 角色登场 & 主角能力阶梯",
        "## 时间线结构",
        "## 结局形状线索",
        "## 证据不足项",
    ],
)
def test_build_skeleton_reduce_prompt_contains_all_fixed_headers(header: str) -> None:
    prompt = build_skeleton_reduce_prompt(
        sketches=SKETCHES,
        classification=CLASSIFICATION,
        chunk_count=len(SKETCHES),
    )

    assert header in prompt


def test_build_skeleton_reduce_prompt_enforces_token_ceiling_and_anti_fabrication() -> None:
    prompt = build_skeleton_reduce_prompt(
        sketches=SKETCHES,
        classification=CLASSIFICATION,
        chunk_count=len(SKETCHES),
    )

    assert "整份骨架合计不得超过约 2500 tokens" in prompt
    assert "若证据不足，宁可在“证据不足项”中声明，不要凭空臆断" in prompt


def test_build_skeleton_reduce_prompt_embeds_classification_and_chunk_count() -> None:
    prompt = build_skeleton_reduce_prompt(
        sketches=SKETCHES,
        classification=CLASSIFICATION,
        chunk_count=123,
    )

    assert json.dumps(CLASSIFICATION, ensure_ascii=False) in prompt
    assert "chunk 总数：123" in prompt
    # Sketches serialised as JSON in sorted order
    assert json.dumps(SKETCHES, ensure_ascii=False) in prompt


def test_build_skeleton_reduce_prompt_acknowledges_sub_skeleton_inputs() -> None:
    prompt = build_skeleton_reduce_prompt(
        sketches=SKETCHES,
        classification=CLASSIFICATION,
        chunk_count=len(SKETCHES),
    )

    # Reducer must be tolerant of either sketch dicts or sub-skeleton dicts
    assert "子骨架" in prompt


# --------------------------------------------------------------------------- #
#  Skeleton group reduce prompt                                               #
# --------------------------------------------------------------------------- #


def test_build_skeleton_group_reduce_prompt_labels_group_and_bounds_inference() -> None:
    prompt = build_skeleton_group_reduce_prompt(
        group_sketches=SKETCHES,
        group_index=2,
        group_count=5,
        classification=CLASSIFICATION,
    )

    # Required literal labelling for the sub-skeleton prompt
    assert "当前是 group 3/5 的子骨架" in prompt
    assert "仅基于传入的 sketch 范围，不要推断外部 chunk" in prompt


@pytest.mark.parametrize(
    "header",
    [
        "# 全书骨架",
        "## 阶段划分（按 chunk 索引）",
        "## 主线推进链",
        "## 证据不足项",
    ],
)
def test_build_skeleton_group_reduce_prompt_reuses_skeleton_template(header: str) -> None:
    prompt = build_skeleton_group_reduce_prompt(
        group_sketches=SKETCHES,
        group_index=0,
        group_count=1,
        classification=CLASSIFICATION,
    )

    assert header in prompt


def test_build_skeleton_group_reduce_prompt_serialises_group_sketches() -> None:
    prompt = build_skeleton_group_reduce_prompt(
        group_sketches=SKETCHES,
        group_index=0,
        group_count=1,
        classification=CLASSIFICATION,
    )

    assert json.dumps(SKETCHES, ensure_ascii=False) in prompt


# --------------------------------------------------------------------------- #
#  build_chunk_analysis_prompt — extended with plot_skeleton                  #
# --------------------------------------------------------------------------- #


def test_build_chunk_analysis_prompt_omits_blank_skeleton_context() -> None:
    prompt_default = build_chunk_analysis_prompt(
        chunk="片段",
        chunk_index=0,
        classification=CLASSIFICATION,
        chunk_count=1,
    )
    assert _SKELETON_HEADER not in prompt_default
    assert _SKELETON_CAVEAT not in prompt_default
    assert "主分析文本（当前 chunk，结论优先以此为准）:\n片段" in prompt_default
    assert "## 3.1 阶段划分与字数节奏" in prompt_default


@pytest.mark.parametrize("skeleton", [None, "", "   \n\t  "])
def test_build_chunk_analysis_prompt_treats_blank_skeleton_as_absent(skeleton: str | None) -> None:
    prompt = build_chunk_analysis_prompt(
        chunk="片段",
        chunk_index=0,
        classification=CLASSIFICATION,
        chunk_count=1,
        plot_skeleton=skeleton,
    )

    assert _SKELETON_HEADER not in prompt


def test_build_chunk_analysis_prompt_with_skeleton_injects_section_and_caveat() -> None:
    prompt = build_chunk_analysis_prompt(
        chunk="片段",
        chunk_index=0,
        classification=CLASSIFICATION,
        chunk_count=1,
        plot_skeleton=_SAMPLE_SKELETON,
    )

    assert _SKELETON_HEADER in prompt
    assert "启动期 0-1；上升期 2-3" in prompt
    assert _SKELETON_CAVEAT in prompt
    # Skeleton block must precede the chunk text (the "input fragment")
    assert prompt.index(_SKELETON_HEADER) < prompt.index("主分析文本（当前 chunk，结论优先以此为准）")


def test_build_chunk_analysis_prompt_distinguishes_primary_text_and_neighbor_context() -> None:
    prompt = build_chunk_analysis_prompt(
        chunk="主正文片段",
        chunk_index=0,
        classification=CLASSIFICATION,
        chunk_count=1,
        plot_skeleton=_SAMPLE_SKELETON,
        overlap_before="前文补充",
        overlap_after="后文补充",
    )

    assert "主分析文本（当前 chunk，结论优先以此为准）" in prompt
    assert "前邻接上下文（仅用于跨边界补全）" in prompt
    assert "后邻接上下文（仅用于跨边界补全）" in prompt
    assert "不要把纯邻接上下文中的事件重复记为当前 chunk 的独立事件" in prompt


# --------------------------------------------------------------------------- #
#  build_merge_prompt — extended with plot_skeleton                           #
# --------------------------------------------------------------------------- #


def test_build_merge_prompt_omits_blank_skeleton_context() -> None:
    chunk_analyses = [{"chunk_index": 0, "chunk_count": 1, "markdown": "# X"}]
    prompt_default = build_merge_prompt(
        chunk_analyses=chunk_analyses,
        classification=CLASSIFICATION,
    )
    assert _SKELETON_HEADER not in prompt_default
    assert _SKELETON_CAVEAT not in prompt_default


def test_build_merge_prompt_with_skeleton_injects_before_merge_inputs() -> None:
    prompt = build_merge_prompt(
        chunk_analyses=[{"chunk_index": 0, "chunk_count": 1, "markdown": "# X"}],
        classification=CLASSIFICATION,
        plot_skeleton=_SAMPLE_SKELETON,
    )

    assert _SKELETON_HEADER in prompt
    assert _SKELETON_CAVEAT in prompt
    assert "启动期 0-1；上升期 2-3" in prompt
    assert prompt.index(_SKELETON_HEADER) < prompt.index("待合并结果：")


# --------------------------------------------------------------------------- #
#  build_report_prompt — extended with plot_skeleton                          #
# --------------------------------------------------------------------------- #


_REPORT_SKELETON_HINT = (
    "在生成 3.1 阶段划分、3.2 主爽点线兑现节奏、3.11 结局形状 时应优先参考骨架的阶段与节奏判断。"
)


def test_build_report_prompt_omits_blank_skeleton_context() -> None:
    prompt_default = build_report_prompt(
        merged_analysis_markdown="# 聚合草稿",
        classification=CLASSIFICATION,
    )
    assert _SKELETON_HEADER not in prompt_default
    assert _REPORT_SKELETON_HINT not in prompt_default


def test_build_report_prompt_with_skeleton_injects_section_and_hint_before_inputs() -> None:
    prompt = build_report_prompt(
        merged_analysis_markdown="# 聚合草稿",
        classification=CLASSIFICATION,
        plot_skeleton=_SAMPLE_SKELETON,
    )

    assert _SKELETON_HEADER in prompt
    assert _SKELETON_CAVEAT in prompt
    assert "启动期 0-1；上升期 2-3" in prompt
    # The report-specific hint is appended only when a skeleton is provided
    assert _REPORT_SKELETON_HINT in prompt
    # Both skeleton section and the hint must appear before the merged result payload
    assert prompt.index(_SKELETON_HEADER) < prompt.index("聚合结果：")
    assert prompt.index(_REPORT_SKELETON_HINT) < prompt.index("聚合结果：")


# --------------------------------------------------------------------------- #
#  build_prompt_pack_prompt                                                   #
# --------------------------------------------------------------------------- #


def test_build_prompt_pack_prompt_forbids_explanatory_preface_and_requires_direct_section_start() -> None:
    prompt = build_prompt_pack_prompt(
        report_markdown=_REPORT_MARKDOWN,
        plot_summary_markdown=_PLOT_SUMMARY_MARKDOWN,
    )

    assert "输出必须直接从 `# Shared Constraints` 开始" in prompt
    assert "不要输出任何前言、任务说明、来源说明" in prompt
    assert "不要写“好的”" in prompt
    assert "不要写“作为”" in prompt
    assert "不得依赖“分析报告”这一上文存在" in prompt


def test_build_prompt_pack_prompt_template_covers_bible_and_writing_contexts() -> None:
    prompt = build_prompt_pack_prompt(
        report_markdown=_REPORT_MARKDOWN,
        plot_summary_markdown=_PLOT_SUMMARY_MARKDOWN,
    )

    for heading in (
        "# Worldbuilding Prompt",
        "# Character Cards Prompt",
        "# Outline Master Prompt",
        "# Volume Planning Prompt",
        "# Chapter Outline Prompt",
        "# Beat Planning Prompt",
        "# Continuation Guardrails",
    ):
        assert heading in prompt

    assert "世界观设定、角色卡、总纲、分卷规划、章节细纲、节拍规划和正文续写" in prompt
    assert "Plot 是结构约束，不是内容模板" in prompt
    assert "不得照搬样本角色、设定、事件" in prompt


def test_build_prompt_pack_prompt_requires_de_sampling_and_prototype_rewrites() -> None:
    prompt = build_prompt_pack_prompt(
        report_markdown=_REPORT_MARKDOWN,
        plot_summary_markdown=_PLOT_SUMMARY_MARKDOWN,
    )

    assert "人物名必须改写为角色原型" in prompt
    assert "专属资源必须改写为资源原型" in prompt
    assert "专属事件必须改写为冲突原型" in prompt
    assert "禁止保留章节号、chunk 编号、样本专名、原作特有固有名词" in prompt
    assert "师门权威、高位女性角色、异族继承者、竞争型反派、指导型强者" in prompt
    assert "核心稀缺资源、身份逆转筹码、境界突破媒介、血脉级利益" in prompt
    assert "胁迫性绑定、被迫接受的契约、资源争夺引发的反转、由信息差触发的控制关系" in prompt


def test_build_prompt_pack_prompt_limits_few_shot_to_abstract_prototypes_and_slots() -> None:
    prompt = build_prompt_pack_prompt(
        report_markdown=_REPORT_MARKDOWN,
        plot_summary_markdown=_PLOT_SUMMARY_MARKDOWN,
    )

    assert "Few-shot 只允许使用原型词与显式槽位" in prompt
    assert "高位角色、反派、关键关系对象、宗门权威、核心资源、绑定关系、突破机会" in prompt
    assert "[角色A]" in prompt
    assert "[高位角色B]" in prompt
    assert "[资源C]" in prompt
    assert "[场景D]" in prompt
    assert "[弱点E]" in prompt
    assert "禁止出现原样本人物名、原样本事件名、原样本世界观专属名词" in prompt
