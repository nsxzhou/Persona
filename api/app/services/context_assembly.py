"""上下文组装服务。

将 Voice Profile、Plot Writing Guide、Intensity Profile 和项目上下文组装为完整的 LLM 系统提示词。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.length_presets import LengthPresetKey, get_progress
from app.prompts.novel_shared import build_pov_mode_hint
from app.schemas.prompt_profiles import (
    ChapterObjectiveCard,
    GenerationProfile,
    IntensityProfile,
    VoiceProfile,
    build_chapter_objective_card,
    build_intensity_profile,
    default_generation_profile,
    derive_voice_profile,
)

STORY_SUMMARY_CONTEXT_BUDGET = 4000
WORLD_BUILDING_CONTEXT_BUDGET = 4000
OUTLINE_MASTER_CONTEXT_BUDGET = 3000
OUTLINE_DETAIL_CONTEXT_BUDGET = 7000
RUNTIME_STATE_CONTEXT_BUDGET = 5000
RUNTIME_THREADS_CONTEXT_BUDGET = 4000

_TRUNCATED_MARKER = "\n\n（已按上下文预算截断）"


_PLOT_APPLICATION_RULES = """

- 不要把 Plot Writing Guide 当成背景参考；每次正文生成都要让它显式改变当前章节的推进选择。
- 每次正文生成至少推进信息差、利益绑定、资源兑现、关系重组或新压力中的一项。
- 关系张力必须承担剧情功能：奖励源、阻力源、情绪牵引源、身份压迫源或未兑现承诺。
- 强度档位改变欲望的落地方式，不改变剧情推进义务。
"""


_WRITING_RULES = """

- 展示不讲述（Show, Don't Tell）：用动作、对话、细节展现情感和性格
- 对话要有潜台词：每句对话应揭示角色性格或推动情节，禁止纯信息传递的水词
- 五感沉浸：每个新场景至少调用 2 种感官描写

### 节奏控制
- 保持快节奏：删除不必要的过渡和心理赘述
- 段落控制：单段不超过 150 字，适配移动端阅读
- 句式偏短：动作场景用短句加快节奏，情感场景可适当放长

### 禁止事项
- 不要以总结性语句开头（如「经过一番思考，他决定...」）
- 不要使用上帝视角泄露其他角色心理（除非叙事视角允许）
- 不要重复前文已述内容
- 直接输出正文，不要添加解释、前言或元评论
"""


@dataclass(frozen=True)
class WritingContextSections:
    description: str = ""
    world_building: str = ""
    characters_blueprint: str = ""
    outline_master: str = ""
    outline_detail: str = ""
    characters_status: str = ""
    runtime_state: str = ""
    runtime_threads: str = ""
    story_summary: str = ""
    active_character_focus: str = ""


def assemble_writing_context(
    style_prompt: str | None = None,
    *,
    plot_prompt: str | None = None,
    voice_profile_markdown: str | None = None,
    story_engine_markdown: str | None = None,
    intensity_profile: IntensityProfile | None = None,
    generation_profile: GenerationProfile | None = None,
    chapter_objective_card: ChapterObjectiveCard | None = None,
    sections: WritingContextSections | None = None,
    length_preset: LengthPresetKey = "long",
    content_length: int = 0,
) -> str:
    """组装写作系统提示词：六段固定顺序，不再依赖巨型总 prompt。"""
    resolved_sections = sections or WritingContextSections()
    values = {
        "description": resolved_sections.description,
        "world_building": _limit_text(
            resolved_sections.world_building,
            WORLD_BUILDING_CONTEXT_BUDGET,
        ),
        "characters_blueprint": resolved_sections.characters_blueprint,
        "outline_master": _limit_text(
            resolved_sections.outline_master,
            OUTLINE_MASTER_CONTEXT_BUDGET,
        ),
        "outline_detail": _limit_text(
            resolved_sections.outline_detail,
            OUTLINE_DETAIL_CONTEXT_BUDGET,
        ),
        "characters_status": resolved_sections.characters_status,
        "runtime_state": _limit_text(
            resolved_sections.runtime_state,
            RUNTIME_STATE_CONTEXT_BUDGET,
        ),
        "runtime_threads": _limit_text(
            resolved_sections.runtime_threads,
            RUNTIME_THREADS_CONTEXT_BUDGET,
        ),
        "story_summary": _limit_text(
            resolved_sections.story_summary,
            STORY_SUMMARY_CONTEXT_BUDGET,
        ),
    }

    resolved_voice_markdown = (voice_profile_markdown or style_prompt or "").strip()
    resolved_story_markdown = (story_engine_markdown or plot_prompt or "").strip()
    resolved_voice_payload: VoiceProfile = derive_voice_profile(resolved_voice_markdown)
    resolved_generation_profile = generation_profile or default_generation_profile()
    resolved_intensity_profile = intensity_profile or build_intensity_profile(resolved_generation_profile)
    resolved_objective_card = chapter_objective_card or build_chapter_objective_card(
        resolved_generation_profile,
        current_chapter_context=resolved_sections.outline_detail,
        outline_detail=resolved_sections.outline_detail,
    )

    context_sections: list[str] = []
    writing_section_order = [
        ("简介", "description"),
        ("故事摘要", "story_summary"),
        ("世界观设定", "world_building"),
        ("总纲", "outline_master"),
        ("分卷与章节细纲", "outline_detail"),
        ("角色基础设定", "characters_blueprint"),
        ("角色动态状态", "characters_status"),
        ("运行时状态", "runtime_state"),
        ("伏笔与线索追踪", "runtime_threads"),
    ]
    for label, key in writing_section_order:
        text = values[key].strip()
        if text:
            context_sections.append(f"## {label}\n\n{text}")

    active_character_focus = resolved_sections.active_character_focus.strip()
    parts: list[str] = [
        "# Output Contract\n"
        "- 直接输出正文。\n"
        "- 禁止前言、自述、总结、初始化说明、显式 thinking。\n"
        "- 不要解释你如何理解规则，不要输出任何元评论。",
        "# Chapter Objective Card\n"
        + _format_mapping(
            {
                "chapter_goal": resolved_objective_card.chapter_goal,
                "payoff_target": resolved_objective_card.payoff_target,
                "pressure_source": resolved_objective_card.pressure_source,
                "relationship_delta": resolved_objective_card.relationship_delta,
                "adult_expression_mode": resolved_objective_card.adult_expression_mode,
                "hook_type": resolved_objective_card.hook_type,
            }
        ),
        "# Active Character Focus\n"
        + (
            active_character_focus
            if active_character_focus
            else "（未识别到明确活跃角色；按当前章节上下文保持人物一致。）"
        ),
        "# Voice Profile\n" + _strip_duplicate_top_heading(resolved_voice_markdown, "# Voice Profile"),
        "# Plot Writing Guide\n"
        + _strip_duplicate_top_heading(resolved_story_markdown, "# Plot Writing Guide")
        + "\n\n## Runtime Guardrails\n"
        + _PLOT_APPLICATION_RULES.strip(),
        "# Intensity Profile\n"
        + _format_mapping(
            {
                "genre_mother": resolved_generation_profile.genre_mother,
                "pov_mode": resolved_generation_profile.pov_mode,
                "intensity_level": resolved_intensity_profile.intensity_level,
                "desire_overlays": ", ".join(resolved_intensity_profile.desire_overlays) or "none",
                "expression_focus": "; ".join(resolved_intensity_profile.expression_focus),
                "boundary_rules": "; ".join(resolved_intensity_profile.boundary_rules),
                "soft_conflicts": "; ".join(resolved_intensity_profile.soft_conflicts) or "none",
            }
        )
        + build_pov_mode_hint(resolved_generation_profile.pov_mode),
    ]

    project_context_parts: list[str] = []
    if context_sections:
        project_context_parts.append("\n\n".join(context_sections))
    project_context_parts.append("## Writing Rules\n" + _WRITING_RULES.strip())

    # 收束引导：根据进度 phase 追加提示
    if content_length > 0:
        progress = get_progress(content_length, length_preset)
        if progress["phase"] == "ending_zone":
            project_context_parts.append(
                f"## 收束引导\n\n"
                f"当前进度已达目标篇幅的 {progress['percentage']}%，"
                f"请开始引导故事走向结局：\n"
                f"- 不要开启新的情节线或引入新角色\n"
                f"- 开始回收已埋下的伏笔\n"
                f"- 情节向核心冲突的最终解决方向收束\n"
                f"- 节奏可以适当加快，推向高潮"
            )
        elif progress["phase"] == "over_target":
            project_context_parts.append(
                f"## 超出目标提醒\n\n"
                f"已超出目标篇幅上限（{progress['target_max']:,} 字），"
                f"请尽快收束故事：\n"
                f"- 必须在接下来的内容中完成结局\n"
                f"- 不要添加任何新元素\n"
                f"- 直接推进到最终结局"
            )

    parts.append("# Project Context\n" + "\n\n".join(project_context_parts))

    return "\n".join(parts)


def _strip_duplicate_top_heading(markdown: str, heading: str) -> str:
    stripped = markdown.strip()
    if stripped.startswith(heading):
        return stripped[len(heading):].lstrip()
    return stripped


def _format_mapping(values: dict[str, str]) -> str:
    return "\n".join(f"{key}: {value}" for key, value in values.items())


def _limit_text(text: str, max_chars: int) -> str:
    stripped = (text or "").strip()
    if len(stripped) <= max_chars:
        return stripped
    body_budget = max(max_chars - len(_TRUNCATED_MARKER), 0)
    return stripped[:body_budget].rstrip() + _TRUNCATED_MARKER
