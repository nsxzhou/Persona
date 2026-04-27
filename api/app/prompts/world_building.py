from __future__ import annotations

from app.core.length_presets import LengthPresetKey
from app.prompts.common import REGENERATION_GUIDANCE
from app.prompts.novel_shared import (
    append_profile_blocks,
    append_soft_length_hint,
    get_hook_framework,
)
from app.prompts.section_context import build_section_user_message
from app.schemas.prompt_profiles import GenerationProfile

_WORLD_BUILDING_INSTRUCTION_TEMPLATE = (
    "请基于简介和已有上下文，生成一份足以支撑人物、冲突和前期展开的必要设定。\n\n"
    "生成前先做隐式判断，不要把判断过程写出来：\n"
    "1. 先判断这部作品更接近哪种题材；"
    "2. 再判断哪些设定模块对当前故事真正必要；"
    "3. 若简介未明确写出超自然，则默认不存在超自然；"
    "4. 只保留当前故事真正需要的模块，只生成当前故事真正需要的模块，不追求完美。\n\n"
    "世界观不是资料库，而是主角欲望和读者期待的供给系统；设定可以是极端的阶层落差与禁忌秩序，或者是为了让主角装逼打脸、开后宫而量身定制的无敌金手指与系统。\n\n"
    "必须使用三维世界构建法，但不要输出推理过程：\n"
    "- 物理维度、社会维度、隐喻维度都要服务角色冲突\n"
    "- 每个维度至少给出一条会影响角色选择的断层线\n"
    "- 写清世界基本法则、薄弱点或可被利用的漏洞\n\n"
    "先写必需模块：\n"
    "1. **时代与秩序**\n"
    "2. **当前局势与核心冲突土壤**\n"
    "3. **主角当前处境与约束（或核心金手指/系统）**\n\n"
    "仅在确有需要时，才补充下列可选模块：\n"
    "- **特殊设定（仅简介明示时）**\n"
    "- **主要势力**\n"
    "- **关键前史**\n"
    "- **活动空间与扩展方向**\n"
    "- **资源与利益流动**\n\n"
    "收束规则：\n"
    "- 历史、权谋、现实、悬疑等题材，不要默认生成公开修炼体系或全民力量系统\n"
    "- 资源争夺并非主线时，不要专门发明货币、修炼材料、交易媒介\n"
    "- 不要为了显得完整而补完世界\n"
    "- 不要发明暂时不会进入剧情的设定\n"
    "{hook_framework}\n"
)


def build_world_building_system_prompt(
    style_prompt: str | None = None,
    plot_prompt: str | None = None,
    generation_profile: GenerationProfile | None = None,
    length_preset: LengthPresetKey = "long",
    regenerating: bool = False,
) -> str:
    hook_framework = get_hook_framework(generation_profile)
    instruction = append_soft_length_hint(
        _WORLD_BUILDING_INSTRUCTION_TEMPLATE.format(hook_framework=hook_framework),
        length_preset,
    )
    parts: list[str] = []
    append_profile_blocks(
        parts,
        style_prompt=style_prompt,
        plot_prompt=plot_prompt,
        plot_usage="只吸收压力系统、推进节奏、角色功能位和兑现逻辑，不得照搬样本角色、设定、事件。",
        generation_profile=generation_profile,
    )
    parts.append(
        "你是一位起点白金作家，正在为自己的新书只保留真正必要的设定，现在要完成「世界观设定」。\n"
        f"{instruction}\n\n"
        "输出要求：\n"
        "- 使用 Markdown 格式，标题层级清晰\n"
        "- 具体且有用，避免空泛概括\n"
        "- 直接输出内容，不要添加任何解释性前言或总结"
    )
    if regenerating:
        parts.append(REGENERATION_GUIDANCE)
    return "\n".join(parts)


def build_world_building_user_message(
    context: dict[str, str],
    previous_output: str | None = None,
    user_feedback: str | None = None,
) -> str:
    return build_section_user_message(
        "world_building",
        context,
        previous_output=previous_output,
        user_feedback=user_feedback,
    )
