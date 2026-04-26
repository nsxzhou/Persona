from __future__ import annotations

import json
from typing import Any

from app.prompts.plot_analysis import STORY_ENGINE_TEMPLATE
from app.services.plot_analysis_prompts import (
    build_chunk_analysis_prompt,
    build_report_prompt,
    build_skeleton_group_reduce_prompt,
    build_skeleton_reduce_prompt,
    build_sketch_prompt,
    build_story_engine_prompt,
)


CLASSIFICATION: dict[str, Any] = {
    "text_type": "novel",
    "has_timestamps": False,
    "has_speaker_labels": False,
    "has_noise_markers": False,
    "uses_batch_processing": True,
    "location_indexing": "chunk",
}

SAMPLE_SKELETON = (
    "# 全书骨架\n"
    "## 阶段划分（按 chunk 索引）\n"
    "启动期 0-2；拉升期 3-8"
)


def test_build_sketch_prompt_contains_required_json_fields_and_enums() -> None:
    prompt = build_sketch_prompt(
        chunk="示例段落：主角在宗门大比现场出场。",
        chunk_index=0,
        chunk_count=100,
        classification=CLASSIFICATION,
    )

    for field in (
        "chunk_index",
        "chunk_count",
        "characters_present",
        "scene_units",
        "main_events",
        "side_threads",
        "payoff_points",
        "tension_points",
        "hooks",
        "setup_payoff_links",
        "pacing_shift",
        "sample_coverage",
    ):
        assert field in prompt
    for value in ("linear", "flashback", "unclear"):
        assert value in prompt
    assert "只记录当前 chunk 的直接证据" in prompt
    assert "邻接上下文不能覆盖当前 chunk 的事件归属" in prompt
    assert "只分析上传样本" in prompt
    assert "不得推断完整小说" in prompt


def test_build_skeleton_reduce_prompt_keeps_fixed_headers() -> None:
    prompt = build_skeleton_reduce_prompt(
        sketches=[
            {
                "chunk_index": 0,
                "chunk_count": 2,
                "characters_present": ["主角"],
                "scene_units": ["宗门大比现场：主角被压制后被迫应战"],
                "main_events": ["主角被压制"],
                "side_threads": [],
                "payoff_points": ["主角展示能力"],
                "tension_points": ["宗门压力升级"],
                "hooks": ["考核结果未揭晓"],
                "setup_payoff_links": ["前置羞辱 -> 当场反击"],
                "pacing_shift": "压迫转入反击",
                "time_marker": "linear",
                "sample_coverage": ["opening_seen", "development_seen"],
            }
        ],
        classification=CLASSIFICATION,
        chunk_count=1,
    )

    for header in (
        "# 全书骨架",
        "## 样本覆盖范围",
        "## 主线推进链",
        "## 支线线索",
        "## 场景账本",
        "## 爽点与钩子",
        "## 节奏曲线",
        "## 证据不足项",
    ):
        assert header in prompt
    assert "只分析上传样本" in prompt
    assert "不得推断完整小说" in prompt
    assert "未覆盖开篇、高潮或结尾" in prompt


def test_build_chunk_analysis_and_report_prompts_thread_skeleton_context() -> None:
    chunk_prompt = build_chunk_analysis_prompt(
        chunk="主角被宗门压制。",
        chunk_index=1,
        classification=CLASSIFICATION,
        chunk_count=3,
        plot_skeleton=SAMPLE_SKELETON,
    )
    report_prompt = build_report_prompt(
        merged_analysis_markdown="# 执行摘要\n聚合结果",
        classification=CLASSIFICATION,
        plot_skeleton=SAMPLE_SKELETON,
    )

    assert "## 全书骨架（参考上下文）" in chunk_prompt
    assert "骨架仅用于定位与上下文参考" in chunk_prompt
    assert "## 全书骨架（参考上下文）" in report_prompt
    assert "推进规律 + 证据摘要" in chunk_prompt
    assert "不要只写事件复述" in chunk_prompt
    for header in (
        "## 2.5.1 主线剧情分析",
        "## 2.5.2 支线剧情分析",
        "## 2.5.3 细纲",
        "## 2.5.4 场景纲",
        "## 2.5.5 爽点",
        "## 2.5.6 节奏",
    ):
        assert header in report_prompt
    assert "只分析上传样本" in report_prompt
    assert "当前样本未覆盖" in report_prompt


def test_build_story_engine_prompt_requires_new_heading_and_sections() -> None:
    prompt = build_story_engine_prompt(
        report_markdown="# 执行摘要\n男频高压推进。",
        plot_name="宗门夺位",
    )

    assert "生成一个可复用的 Plot Writing Guide" in prompt
    assert "输出必须直接从 `# Plot Writing Guide` 开始" in prompt
    for section in (
        "## Core Plot Formula",
        "## Chapter Progression Loop",
        "## Scene Construction Rules",
        "## Setup and Payoff Rules",
        "## Payoff and Tension Rhythm",
        "## Side Plot Usage",
        "## Hook Recipes",
        "## Anti-Drift Rules",
    ):
        assert section in prompt


def test_build_story_engine_prompt_outputs_teaching_rules_not_analysis_recap() -> None:
    prompt = build_story_engine_prompt(
        report_markdown="# 执行摘要\n样本包含后宫、曹贼和控制倾向。",
        plot_name="宗门夺位",
    )

    assert "不要复述分析报告" in prompt
    assert "禁止保留样本人物名、地名、势力名、事件名" in prompt
    assert "genre_mother" not in prompt
    assert "suggested_overlays" not in prompt


def test_story_engine_template_matches_runtime_contract() -> None:
    assert STORY_ENGINE_TEMPLATE.startswith("# Plot Writing Guide")
    assert "## Core Plot Formula" in STORY_ENGINE_TEMPLATE
    assert "## Anti-Drift Rules" in STORY_ENGINE_TEMPLATE
    assert "genre_mother" not in STORY_ENGINE_TEMPLATE
    assert "suggested_overlays" not in STORY_ENGINE_TEMPLATE
    assert "Tone Lock" not in STORY_ENGINE_TEMPLATE


def test_skeleton_group_reduce_prompt_keeps_group_bounds() -> None:
    prompt = build_skeleton_group_reduce_prompt(
        group_sketches=[],
        group_index=2,
        group_count=5,
        classification=CLASSIFICATION,
    )

    assert "group 3/5" in prompt
    assert json.dumps(CLASSIFICATION, ensure_ascii=False) in prompt
