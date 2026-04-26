from __future__ import annotations

import importlib

from app.services.context_assembly import WritingContextSections, assemble_writing_context


def test_writing_context_uses_fixed_six_section_order() -> None:
    module = importlib.import_module("app.schemas.prompt_profiles")
    ChapterObjectiveCard = getattr(module, "ChapterObjectiveCard")
    GenerationProfile = getattr(module, "GenerationProfile")
    IntensityProfile = getattr(module, "IntensityProfile")

    prompt = assemble_writing_context(
        voice_profile_markdown=(
            "# Voice Profile\n"
            "## 3.1 口头禅与常用表达\n- 执行规则：短句推进。\n"
        ),
        story_engine_markdown=(
            "# Plot Writing Guide\n"
            "## Core Plot Formula\n- 用压力迫使主角行动。\n"
        ),
        intensity_profile=IntensityProfile(
            intensity_level="explicit",
            desire_overlays=["harem_collect"],
            expression_focus=["占有欲", "身体感官"],
            boundary_rules=["未成年相关绝对移除"],
            soft_conflicts=[],
        ),
        generation_profile=GenerationProfile(
            genre_mother="xianxia",
            desire_overlays=["harem_collect"],
            intensity_level="explicit",
            pov_mode="limited_third",
            morality_axis="ruthless_growth",
            pace_density="fast",
        ),
        chapter_objective_card=ChapterObjectiveCard(
            chapter_goal="seduce",
            payoff_target="relationship",
            pressure_source="宗门压制与名分焦虑",
            relationship_delta="从试探进入默认暧昧绑定",
            adult_expression_mode="explicit",
            hook_type="half_payoff_then_backlash",
        ),
        sections=WritingContextSections(
            description="寒门少年被迫入局。",
            characters="女主是宗门高位角色。",
            outline_detail="本章必须推进关系与境界。",
        ),
    )

    headers = (
        "# Output Contract",
        "# Chapter Objective Card",
        "# Voice Profile",
        "# Plot Writing Guide",
        "# Intensity Profile",
        "# Project Context",
    )

    last_index = -1
    for header in headers:
        current_index = prompt.index(header)
        assert current_index > last_index
        last_index = current_index

    assert "直接输出正文" in prompt
    assert "禁止前言、自述、总结、初始化说明、显式 thinking" in prompt
    assert "genre_mother: xianxia" in prompt
    assert "用压力迫使主角行动" in prompt
    assert "intensity_level: explicit" in prompt
    assert "chapter_goal: seduce" in prompt
