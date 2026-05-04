from __future__ import annotations

from app.core.length_presets import LengthPresetKey, get_planning_budget
from app.prompts.common import REGENERATION_GUIDANCE, append_regeneration_context
from app.schemas.prompt_profiles import GenerationProfile

BEAT_GENERATE_CONTEXT_CHARS = 2000
BEAT_EXPAND_CONTEXT_CHARS = 1500

LENGTH_HINT_LABELS: dict[LengthPresetKey, str] = {
    "short": "预计体量偏短，几万或者十几万字",
    "medium": "预计体量中等，几十万字",
    "long": "预计体量偏长，百万字",
}

MAINSTREAM_HOOK_FRAMEWORK = (
    "\n\n男频核心驱动框架（力量与权力的扩张）：\n"
    "- 明确本阶段的多巴胺来源：极致打脸逆袭、阶级跃升的掌控感。\n"
    "- 明确本阶段的核心期待：主角何时能获得金钱、权力、地位的绝对扩张。\n"
    "- 充分发挥“安全地打破禁忌”带来的背德刺激，但不得偏离项目已明确的题材解释与生成配置。\n"
    "统一强模式约束：\n"
    "- 未成年相关内容绝对禁止\n"
    "- 保持爽文节奏，重点突出升级、暴富、打脸、长生等核心爽点。\n"
)

NSFW_HOOK_FRAMEWORK = (
    "\n\n男频核心驱动框架（力量扩张与欲望满足）：\n"
    "- 明确本阶段的多巴胺来源：极致打脸逆袭、阶级跃升的掌控感、或打破禁忌的背德感。\n"
    "- 明确本阶段的核心期待：主角何时能把高冷/难以企及的角色推倒，或何时将金钱与武力转化为交配权的绝对扩张。\n"
    "- 允许并鼓励纯粹的情感投射与生理唤醒（如多女主/后宫的绝对忠诚与陪伴），允许大量露骨的情绪宣泄或生理刺激描写。\n"
    "- 欲望、征服感、曹贼/绿帽XP、催眠/常识修改、仙子堕落等都可以是核心爽点本身，无需强行挂靠其他剧情功能。\n\n"
    "统一强模式约束：\n"
    "- 未成年相关内容绝对禁止\n"
    "- overlay 与 intensity 由显式配置决定，完全拥抱该档位的全部感官与欲望表现，不要自行降级。\n"
    "- 充分发挥“安全地打破禁忌”带来的背德刺激，满足强烈的反差感和征服欲。\n"
)

PLOT_FINGERPRINT_CONTRACT = (
    "\n\nPlot 指纹落地契约：\n"
    "- 输出中必须让读者看见 Plot Pack 如何改变当前项目，不能只把 Plot Pack 当作背景参考。\n"
    "- 隐式提取并应用 Plot Pack 的核心驱动轴、读者追读问题、节奏约束、角色功能位和禁区。\n"
    "- 允许规划单元完全聚焦于极度的“爽感”、金手指大爆发、或是彻底的欲望/肉体征服。\n"
    "- 正文与节拍可以大段描写纯粹的氛围、文风、暧昧、甚至是极致的欲望满足与生理唤醒。\n"
)

GROUNDED_INTERPRETATION_GUARDRAIL = (
    "\n\n题材收束提醒：\n- 沿用世界观已确定的题材解释，不得臆想毫无根据的设定\n"
)

MALE_COMMERCIAL_ENGINE = (
    "\n\n男频商业驱动内核：\n"
    "- 先判断这本书的主燃料：力量与权力的扩张、欲望满足，或二者叠加。\n"
    "- 每个设定、角色、事件都要挂到可追读的反馈链：压制 -> 反制 -> 兑现 -> 新压力。\n"
    "- 优先制造清晰进度条：升级反馈、资源掠夺、身份逆转、关系占有、势力扩张或禁忌突破。\n"
    "- 爽点不是口号，必须落成可见动作：主角拿到什么、压过谁、夺回什么、征服谁、让谁付出代价。\n"
    "- 主流市场用打脸、暴富、长生、权力扩张和隐晦暧昧承载刺激；NSFW 市场允许把欲望满足、征服欲、背德感和生理唤醒作为主驱动。\n"
    "- 可以充分利用“安全地打破禁忌”的心理张力，但必须服从项目已选择的 target_market、intensity_level 和边界规则。\n"
    "- 每个规划单元都要回答：读者下一章到底在等什么，以及这个期待会在何处半兑现或反噬。\n"
)


def get_hook_framework(generation_profile: GenerationProfile | None) -> str:
    target_market = generation_profile.target_market if generation_profile else "mainstream"
    if target_market == "nsfw":
        return NSFW_HOOK_FRAMEWORK
    return MAINSTREAM_HOOK_FRAMEWORK


def build_soft_length_hint(length_preset: LengthPresetKey) -> str:
    label = LENGTH_HINT_LABELS.get(length_preset, LENGTH_HINT_LABELS["long"])
    return (
        "\n\n篇幅适配提示：\n"
        f"- 当前小说{label}，把它当作展开密度和推进节奏的软参考\n"
        "- 不必为了匹配预设篇幅，硬性限制结构层级、角色数量或设定规模\n"
        "- 以故事实际需要决定哪些部分细写、略写、前置或后置"
    )


def _format_range(value: tuple[int, int]) -> str:
    return f"{value[0]}-{value[1]}"


def build_character_planning_budget_hint(length_preset: LengthPresetKey) -> str:
    budget = get_planning_budget(length_preset)
    character_count = _format_range(budget["character_count"])
    return (
        "\n\n角色池预算提示：\n"
        f"- 关键角色池目标：{character_count} 个；这里指长期有叙事功能的关键角色，不包含临时 NPC\n"
        "- 角色不是设定展示位，而是追读功能位；先满足角色池数量，再按重要程度分配详略\n"
        "- T0：主角，完整动力学详卡；T0 主角承担欲望入口、升级反馈和最终胜负\n"
        "- T1：核心关系人/核心对手，较详卡；T1 承担核心压迫、核心奖励、核心背叛或核心关系兑现\n"
        "- T2：重要配角/阶段性阻力/奖励源，轻卡；T2 承担阶段性阻力、资源入口、情绪缓冲或小高潮触发\n"
        "- T3：伏笔角色/后期引线/势力代表，极简卡；T3 只保留一个可回收的钩子\n"
        "- 不要把 T2/T3 写成完整人物小传；他们只需要明确功能、弱点、入场时机和能撬动的爽点\n"
        "- 临时 NPC 和后期新势力角色可以留给后续卷纲、章节生成和记忆同步增补"
    )


def build_outline_closure_hint() -> str:
    return (
        "\n\n全书闭环硬账：\n"
        "- 总纲不是世界设定摘要，而是全书追读承诺；每一阶段都要能看见读者为什么继续翻下一章\n"
        "- 必须覆盖开局局面、核心矛盾、中段升级、终局对抗、结局与余波\n"
        "- 必须写明终局结局/最终代价，不能只写近期方向\n"
        "- 开局压制如何逼主角入局，中段升级如何把金钱、武力、身份或关系转成更大筹码，都要写清\n"
        "- 终局要写清主角最终压过谁、拿到什么、失去或付出什么；余波要留下新的秩序、关系归属或禁忌后果\n"
        "- 结局可以保留执行细节弹性，但主线胜负、代价和余波方向必须明确"
    )


def build_pov_mode_hint(pov_mode: str | None) -> str:
    if pov_mode == "limited_third":
        return (
            "\n\n视角约束：\n"
            "- 使用限制性第三人称，只写当前视角角色能够观察、听见、感受到的内容。\n"
            "- 正文叙事主体必须使用第三人称角色名/他/她承载，不要用“我”作为旁白叙事视角。\n"
            "- “我”只允许出现在角色对白中，不允许出现在非对白叙事句里。\n"
            "- 不要写括号式内心独白，不要写“（心想：……）”“（内心OS：……）”这类显式思考标签。\n"
            "- 不要直接写“我心想”“我觉得”“我暗自”等第一人称内心句式；若需要呈现心理变化，改写成动作、停顿、表情、语气和外部反应。\n"
            "- 不要把全知旁白混进限制视角里。"
        )
    if pov_mode in {"first_person", "deep_first"}:
        return (
            "\n\n视角约束：\n"
            "- 保持单一第一人称视角，不要在叙事中跳出到全知视角。\n"
            "- 内心与动作要保持同一主体，不要混用第三人称旁白。"
        )
    return (
        "\n\n视角约束：\n"
        "- 严格保持单一叙事视角，不要在同一段里混用多重视角。"
    )


def build_volume_planning_budget_hint(length_preset: LengthPresetKey) -> str:
    budget = get_planning_budget(length_preset)
    volume_count = _format_range(budget["volume_count"])
    chapter_count = _format_range(budget["first_volume_chapters"])
    return (
        "\n\n规划预算提示：\n"
        "- 卷纲负责全书追读承诺，章节详纲负责当前卷执行；不要把两层写成同一种目录\n"
        f"- 全书卷级/阶段级规划目标：{volume_count} 个规划块\n"
        f"- 章节详纲默认只详拆首卷或当前卷：{chapter_count} 章\n"
        "- 首卷/当前卷要拆到章末期待：每章发生什么、读者下一章等什么、阶段性兑现如何反噬\n"
        "- 后续卷只保留主驱动轴、兑现物、核心阻力、卷尾推动点和角色状态变化\n"
        "- 每个后续卷至少交代压制来源、半兑现、反噬、新地图或新关系筹码\n"
        "- 后续卷不要虚构完整章节目录，不要一次性把全书所有章节都拆成详纲"
    )


def append_soft_length_hint(instruction: str, length_preset: LengthPresetKey) -> str:
    return instruction + build_soft_length_hint(length_preset)


def format_plot_prompt_pack(
    plot_prompt: str,
    *,
    usage: str,
) -> str:
    return (
        "# Plot Prompt Pack（情节结构约束）\n\n"
        f"{plot_prompt.strip()}\n\n"
        f"使用方式：Plot 是结构约束，不是内容模板；{usage}"
        f"{PLOT_FINGERPRINT_CONTRACT}"
    )


def format_generation_profile(generation_profile: GenerationProfile | None) -> str:
    if generation_profile is None:
        return ""
    return (
        "# Generation Profile（运行时生成约束）\n\n"
        f"target_market: {generation_profile.target_market}\n"
        f"genre_mother: {generation_profile.genre_mother}\n"
        f"desire_overlays: {', '.join(generation_profile.desire_overlays) or 'none'}\n"
        f"intensity_level: {generation_profile.intensity_level}\n"
        f"pov_mode: {generation_profile.pov_mode}\n"
        f"{build_pov_mode_hint(generation_profile.pov_mode)}\n"
        f"morality_axis: {generation_profile.morality_axis}\n"
        f"pace_density: {generation_profile.pace_density}\n\n"
        "这些字段是显式创作目标，必须直接作用于规划与正文生成。"
    )


def append_profile_blocks(
    parts: list[str],
    *,
    style_prompt: str | None,
    plot_prompt: str | None,
    plot_usage: str | None,
    generation_profile: GenerationProfile | None,
) -> None:
    if style_prompt:
        parts.append(style_prompt)
        parts.append("\n\n---\n")
    if plot_prompt and plot_usage:
        parts.append(format_plot_prompt_pack(plot_prompt, usage=plot_usage))
        parts.append("\n\n---\n")
    generation_profile_block = format_generation_profile(generation_profile)
    if generation_profile_block:
        parts.append(generation_profile_block)
        parts.append("\n\n---\n")
