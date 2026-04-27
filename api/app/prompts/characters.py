from __future__ import annotations

from app.core.length_presets import LengthPresetKey
from app.prompts.common import REGENERATION_GUIDANCE
from app.prompts.novel_shared import (
    GROUNDED_INTERPRETATION_GUARDRAIL,
    append_profile_blocks,
    append_soft_length_hint,
    get_hook_framework,
)
from app.prompts.section_context import build_section_user_message
from app.schemas.prompt_profiles import GenerationProfile

_CHARACTER_BLUEPRINT_INSTRUCTION_TEMPLATE = (
    "请基于简介、世界观设定和已有上下文，设计这部小说的主要角色。\n\n"
    "必须使用角色动力学架构，但不要输出思维链：\n"
    "- 每个核心角色都要写清表层目标、深层渴望、灵魂需求\n"
    "- 每个核心角色都要有初始状态 → 触发事件 → 认知失调 → 蜕变节点 → 最终状态\n"
    "- 角色关系网必须包含价值观冲突、合作纽带与背叛风险\n\n"
    "角色信息优先回答以下问题：\n"
    "- 他是谁，为什么此刻会入局\n"
    "- 他如何卡住主角，或为什么能帮主角破局\n"
    "- 主角能利用、交换、规避或反制他的点是什么\n"
    "- 角色能让读者期待主角得到什么、压过什么、推倒谁、彻底征服谁，或是提供绝对忠诚的避风港\n\n"
    "功能分配要求：\n"
    "- 角色群里要有明确的奖励源（如绝色红颜、可掠夺资源）、阻力源、压迫源、反转源、情绪牵引源\n"
    "- 写清短期目标、长期目标、缺陷与可被撬动/攻略的弱点\n"
    "- 允许角色功能完全定位于“满足特定的征服欲”、“XP/欲望投射”或“提供绝对的陪伴与爽感”\n"
    "- 避免只写人设标签或空泛魅力描述\n\n"
    "每个角色用二级标题分隔，内部用结构化列表。"
    "{hook_framework}"
)


def build_character_blueprint_system_prompt(
    style_prompt: str | None = None,
    plot_prompt: str | None = None,
    generation_profile: GenerationProfile | None = None,
    length_preset: LengthPresetKey = "long",
    regenerating: bool = False,
) -> str:
    hook_framework = get_hook_framework(generation_profile)
    instruction = append_soft_length_hint(
        _CHARACTER_BLUEPRINT_INSTRUCTION_TEMPLATE.format(hook_framework=hook_framework),
        length_preset,
    )
    instruction += GROUNDED_INTERPRETATION_GUARDRAIL
    parts: list[str] = []
    append_profile_blocks(
        parts,
        style_prompt=style_prompt,
        plot_prompt=plot_prompt,
        plot_usage="只吸收压力系统、推进节奏、角色功能位和兑现逻辑，不得照搬样本角色、设定、事件。",
        generation_profile=generation_profile,
    )
    parts.append(
        "你是一位起点白金作家，正在为自己的新书搭设定、排结构、拆章法，现在要完成「角色基础设定」。\n"
        f"{instruction}\n\n"
        "输出要求：\n"
        "- 使用 Markdown 格式，标题层级清晰\n"
        "- 具体且有用，避免空泛概括\n"
        "- 直接输出内容，不要添加任何解释性前言或总结"
    )
    if regenerating:
        parts.append(REGENERATION_GUIDANCE)
    return "\n".join(parts)


def build_character_blueprint_user_message(
    context: dict[str, str],
    previous_output: str | None = None,
    user_feedback: str | None = None,
) -> str:
    return build_section_user_message(
        "characters_blueprint",
        context,
        previous_output=previous_output,
        user_feedback=user_feedback,
    )
