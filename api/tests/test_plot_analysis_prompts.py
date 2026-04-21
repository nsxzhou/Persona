from __future__ import annotations

import json
from typing import Any

import pytest

from app.services.plot_analysis_prompts import (
    build_chunk_analysis_prompt,
    build_merge_prompt,
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


def test_build_chunk_analysis_prompt_without_skeleton_is_backward_compatible() -> None:
    prompt = build_chunk_analysis_prompt(
        chunk="片段",
        chunk_index=0,
        classification=CLASSIFICATION,
        chunk_count=1,
    )

    assert _SKELETON_HEADER not in prompt
    assert _SKELETON_CAVEAT not in prompt
    # Baseline sections still present
    assert "样本文本：\n片段" in prompt
    assert "## 3.1 阶段划分与字数节奏" in prompt


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
    assert prompt.index(_SKELETON_HEADER) < prompt.index("样本文本：")


# --------------------------------------------------------------------------- #
#  build_merge_prompt — extended with plot_skeleton                           #
# --------------------------------------------------------------------------- #


def test_build_merge_prompt_without_skeleton_is_backward_compatible() -> None:
    prompt = build_merge_prompt(
        chunk_analyses=[{"chunk_index": 0, "chunk_count": 1, "markdown": "# X"}],
        classification=CLASSIFICATION,
    )

    assert _SKELETON_HEADER not in prompt
    assert _SKELETON_CAVEAT not in prompt


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


def test_build_report_prompt_without_skeleton_is_backward_compatible() -> None:
    prompt = build_report_prompt(
        merged_analysis_markdown="# 聚合草稿",
        classification=CLASSIFICATION,
    )

    assert _SKELETON_HEADER not in prompt
    assert _REPORT_SKELETON_HINT not in prompt


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
