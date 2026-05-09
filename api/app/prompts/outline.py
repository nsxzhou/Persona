from __future__ import annotations

from app.core.length_presets import LengthPresetKey
from app.prompts.common import REGENERATION_GUIDANCE, append_regeneration_context
from app.prompts.novel_shared import (
    GROUNDED_INTERPRETATION_GUARDRAIL,
    append_profile_blocks,
    append_soft_length_hint,
    build_desire_semantics_hint,
    build_direct_output_rules,
    build_outline_closure_hint,
    build_plot_propulsion_contract,
    build_volume_planning_budget_hint,
    get_commercial_engine,
    get_hook_framework,
)
from app.prompts.section_context import build_section_user_message
from app.schemas.prompt_profiles import GenerationProfile

_OUTLINE_MASTER_INSTRUCTION_TEMPLATE = (
    "从简介、世界观、角色索引/关系网和已有上下文里压出这部小说的总纲。\n\n"
    "必须吸收三幕式情节架构，但不要机械套模板：\n"
    "- 第一幕建立日常异常、催化事件与错误抉择\n"
    "- 第二幕推进双重压力、虚假胜利与灵魂黑夜\n"
    "- 第三幕呈现代价显现、嵌套转折与余波设定\n"
    "- 总纲里必须能看见日常异常、催化事件、虚假胜利、灵魂黑夜、代价显现这些功能点如何落位\n\n"
    "落笔前先做隐式判断，不要把判断过程写出来：\n"
    "- 先判断这本书当前真正靠什么让人继续看下去，是力量、权力、关系、资源还是身份变化的兑现\n"
    "- 围绕同一条主爽点主线组织推进，不要为了显得更大而额外加设定\n"
    "- 不要为了拉大规模而额外铺地图、体系、势力层级\n\n"
    "硬输入检查：\n"
    "- 必须读取并遵守角色索引/关系网、核心角色冻结摘要和占位标记\n"
    "- 必须检查总纲是否覆盖角色功能位、冲突位、奖励位、阻力位和伏笔位\n"
    "- 如果上下文未提供角色索引/关系网，先把缺口写成待补角色功能位或占位说明，不要擅自补成完整人物体系\n"
    "- 如果角色资产缺口仍在，先保留占位或待补说明，不要擅自补成完整人物体系\n\n"
    "以「阶段」为单位规划，每个阶段用二级标题，包含：\n"
    "- **阶段名称与核心命题**\n"
    "- **核心局面/场景**（这一阶段读者主要在追什么局）\n"
    "- **主驱动轴**（本阶段继续服务哪一种核心追读期待）\n"
    "- **当前阶段的核心兑现物**（资源、地位、关系、真相、掌控力、身份反转或规则突破中的哪一项最该兑现）\n"
    "- **阶段核心对手或阻力**（冲突类型和压迫方式）\n"
    "- **主角地位/掌控力变化**（本阶段如何从被动到主动，或从边缘到核心，或者实现绝对掌控）\n"
    "- **角色功能覆盖**（本阶段使用哪些核心角色、次要角色或伏笔角色承担推进）\n"
    "- **核心爽点事件**（1-2 个，必须服务主爽点）\n"
    "- **钩子类型**（悬念、反转、兑现、新压力、关系升温、局势失控中的哪一种）\n"
    "- **阶段末推动点**（悬念、反转、兑现或新压力）\n\n"
    "全局节奏硬账：\n"
    "- 遵循「小高潮-缓冲-大高潮」循环\n"
    "- 开篇尽快建立核心冲突与角色魅力\n"
    "- 每个阶段结束都要推动主爽点进入下一轮兑现\n"
    "- 读者下一阶段最想看主角拿到什么、压过谁、改变什么关系或突破什么规则，必须写清楚\n"
    "- 角色关系如果发生变化，只能是总纲级局部推进，不能在这里把全书角色网络整体洗牌\n"
    "- 核心爽点必须聚焦于极致打脸、资源兑现、权力扩张、身份反转或关系推进；关系变化必须承担明确剧情功能"
    "{hook_framework}"
)

_VOLUME_GENERATE_INSTRUCTION_TEMPLATE = (
    "从总纲和角色索引/关系网里拆出全书整体规划结构。\n\n"
    "每个规划块用二级标题（## ）标注该阶段、卷或幕的名称，必要时可在标题下使用引用行（> ）补充主题、局势或阶段说明。\n"
    "不要输出顶层一级标题（# ），正文必须直接从第一个二级标题（## ）开始。\n"
    "卷级字段只能用项目符号、加粗字段或引用行表达，不要使用三级标题（### ）；三级标题只保留给真实章节。\n"
    "本步骤只生成分卷/阶段规划，禁止输出章节细纲、章节表格、章节范围列表或「第N章」条目；真实章节只能由后续章节细纲步骤以「### 第 N 章：章名」独立输出。\n"
    "不要求固定写成三幕、几卷或多少个阶段，应按总纲中的实际推进自然拆分。\n\n"
    "硬输入检查：\n"
    "- 必须读取并遵守角色索引/关系网、核心角色冻结摘要和占位标记\n"
    "- 如果上下文未提供角色索引/关系网，建议先补角色资产；若用户仍要求继续，只能用待补角色功能位推进，不得自建完整角色体系\n"
    "- 如果角色资产还没补齐，分卷只能做局部推进，不得擅自重排全书角色关系\n\n"
    "卷级规则：\n"
    "- 每一卷都要围绕同一条主驱动轴推进\n"
    "- 写清本卷主打的兑现物，以及它会被谁、用什么方式卡住\n"
    "- 角色只允许在本卷范围内补强、补冲突或补兑现，不允许重写角色底层关系\n"
    "- 节奏上优先考虑压制后兑现、兑现后反噬\n"
    "- 不要把分卷写成只有地图扩大、势力变多的目录扩写\n\n"
    "示例格式：\n"
    "## 第一阶段：入局\n"
    "> 主题：故事正式启动 | 当前压力：旧案逼近\n"
    "{hook_framework}"
)


def build_outline_master_system_prompt(
    style_prompt: str | None = None,
    plot_prompt: str | None = None,
    generation_profile: GenerationProfile | None = None,
    length_preset: LengthPresetKey = "long",
    regenerating: bool = False,
) -> str:
    hook_framework = get_hook_framework(generation_profile) + build_desire_semantics_hint(generation_profile)
    instruction = append_soft_length_hint(
        _OUTLINE_MASTER_INSTRUCTION_TEMPLATE.format(hook_framework=hook_framework),
        length_preset,
    )
    instruction += build_plot_propulsion_contract()
    instruction += build_outline_closure_hint()
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
        "你是一位起点白金作家，正在为自己的新书搭设定、排结构、拆章法，现在要完成「总纲」。\n"
        f"{get_commercial_engine(generation_profile)}"
        f"{instruction}\n\n"
        f"{build_direct_output_rules(extra_rules=('若输出一级标题/书名，必须使用上下文里的「项目小说名（硬约束）」，不得自行拟定新书名',))}"
    )
    if regenerating:
        parts.append(REGENERATION_GUIDANCE)
    return "\n".join(parts)


def build_outline_master_user_message(
    context: dict[str, str],
    previous_output: str | None = None,
    user_feedback: str | None = None,
) -> str:
    return build_section_user_message(
        "outline_master",
        context,
        previous_output=previous_output,
        user_feedback=user_feedback,
    )


def build_volume_generate_system_prompt(
    length_preset: LengthPresetKey = "long",
    style_prompt: str | None = None,
    plot_prompt: str | None = None,
    generation_profile: GenerationProfile | None = None,
    regenerating: bool = False,
) -> str:
    hook_framework = get_hook_framework(generation_profile) + build_desire_semantics_hint(generation_profile)
    instruction = append_soft_length_hint(
        _VOLUME_GENERATE_INSTRUCTION_TEMPLATE.format(hook_framework=hook_framework),
        length_preset,
    )
    instruction += build_plot_propulsion_contract()
    instruction += build_volume_planning_budget_hint(length_preset)
    parts: list[str] = []
    append_profile_blocks(
        parts,
        style_prompt=None,
        plot_prompt=plot_prompt,
        plot_usage="用它规划分卷压力阶梯、兑现节奏、关系状态变化和卷尾新压力，不得照搬样本桥段。",
        generation_profile=generation_profile,
    )
    parts.append(
        "你是一位起点白金作家，正在为自己的新书规划整体结构，梳理分卷规划。\n\n"
        f"{get_commercial_engine(generation_profile)}"
        f"{instruction}\n\n"
        f"{build_direct_output_rules(no_top_level_title=True, extra_rules=('只输出规划结构，不要输出任何章节内容', '不要输出章节表格、章节范围列表或「第N章」条目'))}"
    )
    if regenerating:
        parts.append(REGENERATION_GUIDANCE)
    return "\n".join(parts)


def build_volume_generate_user_message(
    outline_master: str,
    characters_blueprint: str = "",
    previous_output: str | None = None,
    user_feedback: str | None = None,
) -> str:
    parts: list[str] = []
    if characters_blueprint.strip():
        parts.append(f"## 角色索引与关系网\n\n{characters_blueprint}")
    else:
        parts.append("（角色索引与关系网尚未填写，建议先生成 characters_blueprint；若继续生成分卷，只能把角色功能位标成占位，不要自行重写或补全全书角色网络）")
    if outline_master.strip():
        parts.append(f"## 总纲\n\n{outline_master}")
    else:
        parts.append("（总纲尚未填写，建议先生成 outline_master；若继续生成分卷，只能按当前创意做占位式规划。如果角色索引与关系网已存在，也要按其角色关系做局部推进，不要重写全书角色网络）")
    append_regeneration_context(parts, previous_output, user_feedback)
    return "\n\n---\n\n".join(parts)
