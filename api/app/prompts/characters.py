from __future__ import annotations

from app.core.length_presets import LengthPresetKey
from app.prompts.common import REGENERATION_GUIDANCE
from app.prompts.novel_shared import (
    GROUNDED_INTERPRETATION_GUARDRAIL,
    append_profile_blocks,
    append_soft_length_hint,
    build_desire_semantics_hint,
    build_character_planning_budget_hint,
    build_direct_output_rules,
    get_commercial_engine,
    get_hook_framework,
)
from app.prompts.section_context import build_section_user_message
from app.schemas.prompt_profiles import GenerationProfile

_CHARACTER_BLUEPRINT_INSTRUCTION_TEMPLATE = (
    "从简介、世界观设定和已有上下文里先搭出这部小说的角色索引与关系网，再补核心角色卡。\n\n"
    "先画骨架，再填细节，不要把角色一次性写成散装设定堆：\n"
    "- 第一层先输出角色索引/关系图，标明核心角色、次要角色、路人/伏笔角色，以及他们之间的关系方向\n"
    "- 第二层再展开核心角色卡，核心角色必须写清表层目标、深层渴望、灵魂需求\n"
    "- 核心角色必须写出初始状态 → 触发事件 → 认知失调 → 蜕变节点 → 最终状态\n"
    "- 次要角色只保留功能、弱点、场景用途与可撬动点\n"
    "- 路人/伏笔角色只保留可回收钩子或占位说明，不要补全完整人生\n\n"
    "关系网先于人物小传：\n"
    "- 关系网必须包含价值观冲突、合作纽带、背叛风险、资源交换、信息差与情绪牵引\n"
    "- 核心角色之间要明确谁压谁、谁帮谁、谁会背叛谁、谁在后续卷里必须冻结不改\n"
    "- 如当前信息不足，宁可用「占位：待补」标出缺口，也不要替前序资产脑补完整体系\n\n"
    "角色信息优先回答以下问题：\n"
    "- 他是谁，为什么此刻会入局\n"
    "- 他如何卡住主角，或为什么能帮主角破局\n"
    "- 主角能利用、交换、规避或反制他的点是什么\n"
    "- 角色能让读者期待主角得到什么、压过什么、改变什么关系，或获得什么新的资源、筹码与情绪支点\n\n"
    "功能分配规则：\n"
    "- 角色群里要有明确的奖励源、资源入口、阻力源、压迫源、反转源、情绪牵引源\n"
    "- 写清短期目标、长期目标、缺陷与可被撬动/攻略的弱点\n"
    "- 角色功能必须服务主线推进、读者奖励、局势压力或关系张力；不要添加与当前配置无关的关系功能\n"
    "- 冻结规则：已经定义过的核心角色关系、功能位和关键动机，后续只允许局部补强，不允许整组重写\n"
    "- 摘要规则：每个核心角色都要配一条可直接回流到后续总纲/分卷的短摘要\n"
    "- 避免只写人设标签或空泛魅力描述\n\n"
    "输出结构：\n"
    "- 先输出角色索引/关系网，再输出核心角色卡、次要角色卡、路人/伏笔卡\n"
    "- 每个角色或关系组用二级标题分隔，内部用结构化列表\n"
    "- 对缺失信息使用占位标签，不要编造完整背景\n"
    "{hook_framework}"
)


def build_character_blueprint_system_prompt(
    style_prompt: str | None = None,
    plot_prompt: str | None = None,
    generation_profile: GenerationProfile | None = None,
    length_preset: LengthPresetKey = "long",
    regenerating: bool = False,
) -> str:
    hook_framework = get_hook_framework(generation_profile) + build_desire_semantics_hint(generation_profile)
    instruction = append_soft_length_hint(
        _CHARACTER_BLUEPRINT_INSTRUCTION_TEMPLATE.format(hook_framework=hook_framework),
        length_preset,
    )
    instruction += build_character_planning_budget_hint(length_preset)
    instruction += GROUNDED_INTERPRETATION_GUARDRAIL
    parts: list[str] = []
    append_profile_blocks(
        parts,
        style_prompt=None,
        plot_prompt=plot_prompt,
        plot_usage="只吸收压力系统、推进节奏、角色功能位和兑现逻辑，不得照搬样本角色、设定、事件。",
        generation_profile=generation_profile,
    )
    parts.append(
        "你是一位起点白金作家，正在为自己的新书搭设定、排结构、拆章法，现在要完成「角色索引与关系网」。\n"
        f"{get_commercial_engine(generation_profile)}"
        f"{instruction}\n\n"
        f"{build_direct_output_rules()}"
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
