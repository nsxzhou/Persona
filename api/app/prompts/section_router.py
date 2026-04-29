from __future__ import annotations

from app.core.length_presets import LengthPresetKey
from app.prompts.characters import (
    build_character_blueprint_system_prompt,
    build_character_blueprint_user_message,
)
from app.prompts.chapter_plan import (
    build_outline_detail_system_prompt,
    build_outline_detail_user_message,
)
from app.prompts.memory_sync import build_bible_update_user_message
from app.prompts.outline import (
    build_outline_master_system_prompt,
    build_outline_master_user_message,
)
from app.prompts.section_context import build_section_user_message as _build_section_user_message
from app.prompts.world_building import (
    build_world_building_system_prompt,
    build_world_building_user_message,
)
from app.schemas.prompt_profiles import GenerationProfile

VALID_SECTIONS = frozenset(
    {
        "world_building",
        "characters_blueprint",
        "outline_master",
        "outline_detail",
        "characters_status",
        "runtime_state",
        "runtime_threads",
    }
)

_MEMORY_SECTION_INSTRUCTIONS = {
    "characters_status": (
        "你是一位起点白金作家，正在建立开书后的连载状态账本，不是在写角色百科。\n\n"
        "基于已有上下文，为主要角色生成初始动态状态；重点看谁的欲望被撬动、谁欠了债、谁刚得到或失去筹码。\n\n"
        "每个主要角色必须包含：\n"
        "1. **当前位置与处境**\n"
        "2. **伤势/异常状态**\n"
        "3. **关键持有物品**\n"
        "4. **近期关系变化**\n"
        "5. **可被后续撬动的筹码/弱点**\n\n"
        "每个角色用二级标题分隔，内部用结构化列表。\n\n"
        "落笔规则：\n"
        "- 使用 Markdown 格式，标题层级清晰\n"
        "- 具体且有用，避免空泛概括；不要写成角色百科\n"
        "- 直接输出内容，不要添加任何解释性前言或总结"
    ),
    "runtime_state": (
        "你是一位起点白金作家，正在建立剧情总账，只记录会改变后续局面的事件。\n\n"
        "基于已有上下文，生成初始运行时状态；重点记录爽点兑现、压制来源、反噬和新压力，不要复述设定。\n\n"
        "必须包含：\n"
        "1. **时间线** — 关键事件按时序排列\n"
        "2. **角色当前状态** — 各角色的状态变化记录（伤病、关系变化、新出场角色等）\n"
        "3. **新揭示世界规则** — 随剧情发展揭示的世界设定（如某个能力的限制条件、某地的特殊规则等）\n"
        "4. **当前追读压力** — 读者正在等什么兑现、谁在卡住它、下一轮压力来自哪里\n\n"
        "落笔规则：\n"
        "- 使用 Markdown 格式，标题层级清晰\n"
        "- 具体且有用，避免空泛概括\n"
        "- 直接输出内容，不要添加任何解释性前言或总结"
    ),
    "runtime_threads": (
        "你是一位起点白金作家，正在建立追读债务清单，不是在罗列装饰性谜语。\n\n"
        "基于已有上下文，生成初始伏笔与线索追踪；伏笔必须服务后续兑现、反转、打脸、关系突破或禁忌后果。\n\n"
        "必须包含：\n"
        "1. **活跃伏笔** — 尚未回收的悬念/暗示/线索，每条标注类型、埋设位置、重要程度\n"
        "2. **已回收线索** — 已完成回收的伏笔\n"
        "3. **设定约束备忘** — 已确立的硬性设定规则，防止后续写作自相矛盾\n"
        "4. **待兑现债务** — 读者已经被勾起、但还没得到满足的期待\n\n"
        "落笔规则：\n"
        "- 使用 Markdown 格式，标题层级清晰\n"
        "- 具体且有用，避免空泛概括；不要罗列装饰性谜语\n"
        "- 直接输出内容，不要添加任何解释性前言或总结"
    ),
}


def build_section_system_prompt(
    section: str,
    style_prompt: str | None = None,
    plot_prompt: str | None = None,
    generation_profile: GenerationProfile | None = None,
    length_preset: LengthPresetKey = "long",
    regenerating: bool = False,
) -> str:
    if section == "world_building":
        return build_world_building_system_prompt(
            style_prompt=style_prompt,
            plot_prompt=plot_prompt,
            generation_profile=generation_profile,
            length_preset=length_preset,
            regenerating=regenerating,
        )
    if section == "characters_blueprint":
        return build_character_blueprint_system_prompt(
            style_prompt=style_prompt,
            plot_prompt=plot_prompt,
            generation_profile=generation_profile,
            length_preset=length_preset,
            regenerating=regenerating,
        )
    if section == "outline_master":
        return build_outline_master_system_prompt(
            style_prompt=style_prompt,
            plot_prompt=plot_prompt,
            generation_profile=generation_profile,
            length_preset=length_preset,
            regenerating=regenerating,
        )
    if section == "outline_detail":
        return build_outline_detail_system_prompt(
            style_prompt=style_prompt,
            plot_prompt=plot_prompt,
            generation_profile=generation_profile,
            length_preset=length_preset,
            regenerating=regenerating,
        )
    prompt = _MEMORY_SECTION_INSTRUCTIONS[section]
    if regenerating:
        from app.prompts.common import REGENERATION_GUIDANCE

        prompt += REGENERATION_GUIDANCE
    return prompt


def build_section_user_message(
    section: str,
    context: dict[str, str],
    previous_output: str | None = None,
    user_feedback: str | None = None,
) -> str:
    if section == "world_building":
        return build_world_building_user_message(context, previous_output, user_feedback)
    if section == "characters_blueprint":
        return build_character_blueprint_user_message(context, previous_output, user_feedback)
    if section == "outline_master":
        return build_outline_master_user_message(context, previous_output, user_feedback)
    if section == "outline_detail":
        return build_outline_detail_user_message(context, previous_output, user_feedback)
    return _build_section_user_message(section, context, previous_output, user_feedback)
