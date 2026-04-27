from __future__ import annotations

from app.core.length_presets import LengthPresetKey
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
        f"morality_axis: {generation_profile.morality_axis}\n"
        f"pace_density: {generation_profile.pace_density}\n\n"
        "这些字段是显式创作目标，必须直接作用于规划与续写。"
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
