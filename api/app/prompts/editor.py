"""Zen Editor 相关的提示词模板。

包含区块 AI 生成、改写、节拍等各类提示词构建函数。
"""

from __future__ import annotations

import re

from app.core.bible_fields import BIBLE_FIELD_KEYS, BIBLE_FIELD_LABELS
from app.core.domain_errors import UnprocessableEntityError
from app.core.length_presets import LengthPresetKey
from app.prompts.common import REGENERATION_GUIDANCE, append_regeneration_context
from app.schemas.projects import ConceptItem
from app.schemas.prompt_profiles import GenerationProfile

BEAT_GENERATE_CONTEXT_CHARS = 2000
BEAT_EXPAND_CONTEXT_CHARS = 1500


_REGENERATION_GUIDANCE = REGENERATION_GUIDANCE


_append_regeneration_context = append_regeneration_context


def parse_concept_response(raw: str, expected_count: int) -> list[ConceptItem]:
    """Parse LLM concept-generation response ("### 标题\\n\\n摘要" blocks)."""
    text = raw.strip()
    concepts: list[ConceptItem] = []
    for part in re.split(r"^###\s+", text, flags=re.MULTILINE):
        part = part.strip()
        if not part:
            continue
        lines = part.split("\n", 1)
        if len(lines) < 2:
            continue
        title = re.sub(r"^\d+[\.、\s]+", "", lines[0].strip())
        synopsis = lines[1].strip()
        if title and synopsis:
            concepts.append(ConceptItem(title=title, synopsis=synopsis))
    if not concepts:
        raise UnprocessableEntityError("AI 返回的格式无法解析，请重试")
    return concepts[:expected_count]


# --------------------------------------------------------------------------- #
#  Planning instructions with soft length hints                                #
# --------------------------------------------------------------------------- #

_LENGTH_HINT_LABELS: dict[LengthPresetKey, str] = {
    "short": "预计体量偏短，几万或者十几万字",
    "medium": "预计体量中等，几十万字",
    "long": "预计体量偏长，百万字",
}


def _build_soft_length_hint(length_preset: LengthPresetKey) -> str:
    label = _LENGTH_HINT_LABELS.get(length_preset, _LENGTH_HINT_LABELS["long"])
    return (
        "\n\n篇幅适配提示：\n"
        f"- 当前小说{label}，把它当作展开密度和推进节奏的软参考\n"
        "- 不必为了匹配预设篇幅，硬性限制结构层级、角色数量或设定规模\n"
        "- 以故事实际需要决定哪些部分细写、略写、前置或后置"
    )


def _append_soft_length_hint(instruction: str, length_preset: LengthPresetKey) -> str:
    return instruction + _build_soft_length_hint(length_preset)


_MAINSTREAM_HOOK_FRAMEWORK = (
    "\n\n男频核心驱动框架（力量与权力的扩张）：\n"
    "- 明确本阶段的多巴胺来源：极致打脸逆袭、阶级跃升的掌控感。\n"
    "- 明确本阶段的核心期待：主角何时能获得金钱、权力、地位的绝对扩张。\n"
    "统一强模式约束：\n"
    "- 未成年相关内容绝对禁止\n"
    "- 保持爽文节奏，重点突出升级、暴富、打脸、长生等核心爽点。\n"
)

_NSFW_HOOK_FRAMEWORK = (
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

def _get_hook_framework(generation_profile: GenerationProfile | None) -> str:
    target_market = generation_profile.target_market if generation_profile else "mainstream"
    if target_market == "nsfw":
        return _NSFW_HOOK_FRAMEWORK
    return _MAINSTREAM_HOOK_FRAMEWORK


_PLOT_FINGERPRINT_CONTRACT = (
    "\n\nPlot 指纹落地契约：\n"
    "- 输出中必须让读者看见 Plot Pack 如何改变当前项目，不能只把 Plot Pack 当作背景参考。\n"
    "- 隐式提取并应用 Plot Pack 的核心驱动轴、读者追读问题、节奏约束、角色功能位和禁区。\n"
    "- 允许规划单元完全聚焦于极度的“爽感”、金手指大爆发、或是彻底的欲望/肉体征服。\n"
    "- 正文与节拍可以大段描写纯粹的氛围、文风、暧昧、甚至是极致的欲望满足与生理唤醒。\n"
)


def _format_plot_prompt_pack(
    plot_prompt: str,
    *,
    usage: str,
) -> str:
    return (
        "# Plot Prompt Pack（情节结构约束）\n\n"
        f"{plot_prompt.strip()}\n\n"
        f"使用方式：Plot 是结构约束，不是内容模板；{usage}"
        f"{_PLOT_FINGERPRINT_CONTRACT}"
    )


def _format_generation_profile(generation_profile: GenerationProfile | None) -> str:
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


_GROUNDED_INTERPRETATION_GUARDRAIL = (
    "\n\n题材收束提醒：\n- 沿用世界观已确定的题材解释，不得臆想毫无根据的设定\n"
)


_OUTLINE_MASTER_INSTRUCTION_TEMPLATE = (
    "请基于简介、世界观、角色设定和已有上下文，设计这部小说的总纲。\n\n"
    "生成前先做隐式判断，不要把判断过程写出来：\n"
    "- 先判断这本书当前真正靠什么让人继续看下去，是力量与权力的扩张还是欲望的满足\n"
    "- 围绕同一条主爽点主线组织推进，不要为了显得更大而额外加设定\n\n"
    "以「阶段」为单位规划，每个阶段用二级标题，包含：\n"
    "- **阶段名称与核心命题**\n"
    "- **核心局面/场景**（这一阶段读者主要在追什么局）\n"
    "- **主驱动轴**（本阶段继续服务哪一种核心欲望）\n"
    "- **当前阶段的核心兑现物**（资源、地位、关系、真相、掌控力、彻底推倒、打破禁忌中的哪一项最该兑现）\n"
    "- **阶段核心对手或阻力**（冲突类型和压迫方式）\n"
    "- **主角地位/掌控力变化**（本阶段如何从被动到主动，或从边缘到核心，或者实现绝对掌控）\n"
    "- **核心爽点事件**（1-2 个，必须服务主爽点）\n"
    "- **钩子类型**（悬念、反转、兑现、新压力、关系升温、局势失控中的哪一种）\n"
    "- **阶段末推动点**（悬念、反转、兑现或新压力）\n\n"
    "全局节奏要求：\n"
    "- 遵循「小高潮-缓冲-大高潮」循环\n"
    "- 开篇尽快建立核心冲突与角色魅力\n"
    "- 每个阶段结束都要推动主爽点进入下一轮兑现\n"
    "- 读者下一阶段最想看主角拿到什么、压过谁、推倒谁、彻底征服谁，必须写清楚\n"
    "- 允许将核心爽点完全聚焦于极致打脸、后宫扩张或打破禁忌的欲望满足上"
    "{hook_framework}"
)

_OUTLINE_DETAIL_INSTRUCTION_TEMPLATE = (
    "请基于总纲和已有上下文，展开规划结构与章节细纲。\n\n"
    "每个规划块用二级标题（## ）标注该阶段、卷或幕的名称与主题，必要时可在标题下补一行引用（> ）说明当前局面。\n"
    "需要拆到章节时，再在对应规划块下使用三级标题（### ）列出章节。\n"
    "不要求固定写成三幕、几卷或多少章，应由故事实际推进需要决定结构层级。\n\n"
    "每章必须包含：\n"
    "- **章节标题**\n"
    "- **核心事件**（2-3 句话概括）\n"
    "- **情绪走向**（如「平静 → 疑惑 → 震惊 → 愤怒」，或「极致爽感」、「沉沦堕落」）\n"
    "- **章末钩子**（可以是悬念、反转、新压力、关系突破或极致兑现）\n\n"
    "节奏规则：\n"
    "- 同一规划块内的章节情绪应有起伏，但在高潮或欲望满足环节允许连续的情绪宣泄\n"
    "- 允许出现纯粹服务于欲望满足、打脸装逼、后宫日常的章节，无需强求传统局面推进\n"
    "- 该收束时安排伏笔回收和主线收口，但不要机械地按篇幅预设倒推结构\n"
    "- 每章都要回答：下一章读者到底在等什么兑现\n"
    "- 兑现可以是拿到资源、完成打脸、扳回压制、彻底推倒、精神与肉体双重控制或阶层跃升\n"
    "- 悬念必须明确勾着特定的多巴胺反馈、征服欲或生理/情感期待"
    "{hook_framework}"
)

_VOLUME_GENERATE_INSTRUCTION_TEMPLATE = (
    "请基于总纲，设计整体规划结构。\n\n"
    "每个规划块用二级标题（## ）标注该阶段、卷或幕的名称，必要时可在标题下使用引用行（> ）补充主题、局势或阶段说明。\n"
    "不要求固定写成三幕、几卷或多少个阶段，应按总纲中的实际推进自然拆分。\n\n"
    "卷级规则：\n"
    "- 每一卷都要围绕同一条主驱动轴推进\n"
    "- 写清本卷主打的兑现物，以及它会被谁、用什么方式卡住\n"
    "- 节奏上优先考虑压制后兑现、兑现后反噬\n"
    "- 不要把分卷写成只有地图扩大、势力变多的目录扩写\n\n"
    "示例格式：\n"
    "## 第一阶段：入局\n"
    "> 主题：故事正式启动 | 当前压力：旧案逼近\n"
    "{hook_framework}"
)

# --------------------------------------------------------------------------- #
#  Section generation prompts (Step 2)                                         #
# --------------------------------------------------------------------------- #

_SECTION_META: dict[str, dict[str, str]] = {
    "world_building": {
        "label": "世界观设定",
        "instruction_template": (
            "请基于简介和已有上下文，生成一份足以支撑人物、冲突和前期展开的必要设定。\n\n"
            "生成前先做隐式判断，不要把判断过程写出来：\n"
            "1. 先判断这部作品更接近哪种题材；"
            "2. 再判断哪些设定模块对当前故事真正必要；"
            "3. 若简介未明确写出超自然，则默认不存在超自然；"
            "4. 只保留当前故事真正需要的模块，只生成当前故事真正需要的模块，不追求完美。\n\n"
            "世界观不是资料库，而是主角欲望和读者期待的供给系统；设定可以是极端的阶层落差与禁忌秩序，或者是为了让主角装逼打脸、开后宫而量身定制的无敌金手指与系统。\n\n"
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
        ),
    },
    "characters": {
        "label": "角色设定",
        "instruction_template": (
            "请基于简介、世界观设定和已有上下文，设计这部小说的主要角色。\n\n"
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
        ),
    },
    "outline_master": {
        "label": "总纲",
        "instruction_template": _OUTLINE_MASTER_INSTRUCTION_TEMPLATE,
    },
    "outline_detail": {
        "label": "分卷与章节细纲",
        "instruction_template": _OUTLINE_DETAIL_INSTRUCTION_TEMPLATE,
    },
    "runtime_state": {
        "label": "运行时状态",
        "instruction_template": (
            "请基于已有上下文，生成一份初始的运行时状态追踪文档。\n\n"
            "必须包含以下部分：\n"
            "1. **时间线** — 关键事件按时序排列\n"
            "2. **角色当前状态** — 各角色的状态变化记录"
            "（伤病、关系变化、新出场角色等）\n"
            "3. **新揭示世界规则** — 随剧情发展揭示的世界设定"
            "（如某个能力的限制条件、某地的特殊规则等）"
        ),
    },
    "runtime_threads": {
        "label": "伏笔与线索追踪",
        "instruction_template": (
            "请基于已有上下文，生成一份初始的伏笔与线索追踪文档。\n\n"
            "必须包含以下部分：\n"
            "1. **活跃伏笔** — 尚未回收的悬念/暗示/线索，每条标注：\n"
            "   - 类型（设定伏笔/人物伏笔/道具伏笔）\n"
            "   - 埋设位置（大约在哪里出现）\n"
            "   - 重要程度（核心线/支线）\n"
            "2. **已回收线索** — 已完成回收的伏笔\n"
            "3. **设定约束备忘** — 已确立的硬性设定规则"
            "（如某角色的能力限制、某地点的特殊规则等），"
            "防止后续写作出现自相矛盾"
        ),
    },
}

VALID_SECTIONS = frozenset(_SECTION_META.keys())


def build_section_system_prompt(
    section: str,
    style_prompt: str | None = None,
    plot_prompt: str | None = None,
    generation_profile: GenerationProfile | None = None,
    length_preset: LengthPresetKey = "long",
    regenerating: bool = False,
) -> str:
    """构建区块生成的系统提示词（篇幅感知）。"""
    meta = _SECTION_META[section]
    hook_framework = _get_hook_framework(generation_profile)

    # 规划层统一使用主模板，只保留软性的篇幅提示。
    instruction = meta["instruction_template"].format(hook_framework=hook_framework)

    if section == "outline_master":
        instruction = _append_soft_length_hint(instruction, length_preset)
        instruction += _GROUNDED_INTERPRETATION_GUARDRAIL
    elif section == "outline_detail":
        instruction = _append_soft_length_hint(instruction, length_preset)
    else:
        if section in {"world_building", "characters"}:
            instruction = _append_soft_length_hint(instruction, length_preset)
        if section == "characters":
            instruction += _GROUNDED_INTERPRETATION_GUARDRAIL

    parts: list[str] = []
    if style_prompt:
        parts.append(style_prompt)
        parts.append("\n\n---\n")
    if plot_prompt and section in {
        "world_building",
        "characters",
        "outline_master",
        "outline_detail",
    }:
        parts.append(
            _format_plot_prompt_pack(
                plot_prompt,
                usage=(
                    "只吸收压力系统、推进节奏、角色功能位和兑现逻辑，"
                    "不得照搬样本角色、设定、事件。"
                ),
            )
        )
        parts.append("\n\n---\n")
    generation_profile_block = _format_generation_profile(generation_profile)
    if generation_profile_block:
        parts.append(generation_profile_block)
        parts.append("\n\n---\n")
    role_prefix = (
        "你是一位起点白金作家，正在为自己的新书只保留真正必要的设定"
        if section == "world_building"
        else "你是一位起点白金作家，正在为自己的新书搭设定、排结构、拆章法"
    )
    parts.append(
        f"{role_prefix}，现在要完成「{meta['label']}」。\n"
        f"{instruction}\n\n"
        "输出要求：\n"
        "- 使用 Markdown 格式，标题层级清晰\n"
        "- 具体且有用，避免空泛概括\n"
        "- 直接输出内容，不要添加任何解释性前言或总结"
    )
    if regenerating:
        parts.append(_REGENERATION_GUIDANCE)
    return "\n".join(parts)


def build_section_user_message(
    section: str,
    context: dict[str, str],
    previous_output: str | None = None,
    user_feedback: str | None = None,
) -> str:
    """构建区块生成的用户消息，包含已有上下文。"""
    context_parts: list[str] = []
    for key in BIBLE_FIELD_KEYS:
        if key == section:
            continue
        text = context.get(key, "").strip()
        if text:
            label = BIBLE_FIELD_LABELS[key]
            context_parts.append(f"## {label}\n\n{text}")

    parts: list[str] = []
    if context_parts:
        parts.append(
            "以下是当前已有的创作设定：\n\n" + "\n\n---\n\n".join(context_parts)
        )
    else:
        parts.append("（暂无其他已有设定，请基于你的创意自由发挥）")
    _append_regeneration_context(parts, previous_output, user_feedback)
    return "\n\n---\n\n".join(parts)


def build_volume_generate_system_prompt(
    length_preset: LengthPresetKey = "long",
    style_prompt: str | None = None,
    plot_prompt: str | None = None,
    generation_profile: GenerationProfile | None = None,
    regenerating: bool = False,
) -> str:
    """构建卷级结构生成的系统提示词。"""
    hook_framework = _get_hook_framework(generation_profile)
    instruction = _append_soft_length_hint(_VOLUME_GENERATE_INSTRUCTION_TEMPLATE.format(hook_framework=hook_framework), length_preset)
    parts: list[str] = []
    if style_prompt:
        parts.append(style_prompt)
        parts.append("\n\n---\n")
    if plot_prompt:
        parts.append(
            _format_plot_prompt_pack(
                plot_prompt,
                usage="用它规划分卷压力阶梯、兑现节奏、关系状态变化和卷尾新压力，不得照搬样本桥段。",
            )
        )
        parts.append("\n\n---\n")
    generation_profile_block = _format_generation_profile(generation_profile)
    if generation_profile_block:
        parts.append(generation_profile_block)
        parts.append("\n\n---\n")
    parts.append(
        "你是一位起点白金作家，正在为自己的新书规划整体结构，梳理分卷规划。\n\n"
        f"{instruction}\n\n"
        "输出要求：\n"
        "- 使用 Markdown 格式\n"
        "- 只输出规划结构，不要输出任何章节内容\n"
        "- 直接输出内容，不要添加解释性前言或总结"
    )
    if regenerating:
        parts.append(_REGENERATION_GUIDANCE)
    return "\n".join(parts)


def build_volume_generate_user_message(
    outline_master: str,
    previous_output: str | None = None,
    user_feedback: str | None = None,
) -> str:
    """构建卷级结构生成的用户消息。"""
    parts: list[str] = []
    if outline_master.strip():
        parts.append(f"## 总纲\n\n{outline_master}")
    else:
        parts.append("（总纲尚未填写，请基于创意自由规划分卷）")
    _append_regeneration_context(parts, previous_output, user_feedback)
    return "\n\n---\n\n".join(parts)


_VOLUME_CHAPTERS_SYSTEM_TEMPLATE = (
    "你是一位起点白金作家，正在为自己的当前卷拆章节细纲，控制章节推进、情绪起伏和章末钩子。\n\n"
    "为指定的卷设计章节。每章用三级标题（### ），格式如下：\n\n"
    "### 第 N 章：章名\n"
    "- **核心事件**：一句话概括\n"
    "- **情绪走向**：如「平静 → 震惊 → 愤怒」\n"
    "- **章末钩子**：驱动读者继续阅读的悬念或反转\n\n"
    "要求：\n"
    "- 章节之间情绪有起伏，不要连续同一情绪\n"
    "- 每章末必须有钩子\n"
    "- 每章末推动点要能让人立刻知道下一章最想看的兑现是什么\n"
    "- 参考已有的前几卷章节，保持情节连贯\n"
    "- 直接输出章节列表，不要输出卷标题，不要添加解释"
    "{hook_framework}"
)


def build_volume_chapters_system_prompt(
    style_prompt: str | None = None,
    plot_prompt: str | None = None,
    generation_profile: GenerationProfile | None = None,
    regenerating: bool = False,
) -> str:
    """构建单卷章节生成的系统提示词。"""
    parts: list[str] = []
    if style_prompt:
        parts.append(style_prompt)
        parts.append("\n\n---\n")
    if plot_prompt:
        parts.append(
            _format_plot_prompt_pack(
                plot_prompt,
                usage="用它拆章节闭环、章末推动点和关系/资源状态变化，不得照搬样本桥段。",
            )
        )
        parts.append("\n\n---\n")
    generation_profile_block = _format_generation_profile(generation_profile)
    if generation_profile_block:
        parts.append(generation_profile_block)
        parts.append("\n\n---\n")
    hook_framework = _get_hook_framework(generation_profile)
    parts.append(_VOLUME_CHAPTERS_SYSTEM_TEMPLATE.format(hook_framework=hook_framework))
    if regenerating:
        parts.append(_REGENERATION_GUIDANCE)
    return "\n".join(parts)


def build_volume_chapters_user_message(
    outline_master: str,
    volume_title: str,
    volume_meta: str,
    preceding_chapters_summary: str,
    previous_output: str | None = None,
    user_feedback: str | None = None,
) -> str:
    """构建单卷章节生成的用户消息。"""
    parts: list[str] = []
    if outline_master.strip():
        parts.append(f"## 总纲\n\n{outline_master}")
    parts.append(f"## 当前卷\n\n**{volume_title}**\n{volume_meta}")
    if preceding_chapters_summary.strip():
        parts.append(
            f"## 前几卷已有章节（参考，保持连贯）\n\n{preceding_chapters_summary}"
        )
    _append_regeneration_context(parts, previous_output, user_feedback)
    parts.append("请为当前卷设计章节细纲：")
    return "\n\n---\n\n".join(parts)


# --------------------------------------------------------------------------- #
#  Bible update prompts (Step 6)                                               #
# --------------------------------------------------------------------------- #

_BIBLE_UPDATE_SYSTEM = (
    "你是一个设定维护助手，当前任务是：根据刚写出的最新正文，维护和更新项目的【长期 persistent 事件列表】（即运行时状态）和伏笔线索。\n\n"
    "【核心原则】\n"
    "1. 你现在的任务是维护【长期 persistent 事件列表】。严禁像流水账一样记录每章剧情，只能保留对后续章节有长远影响的剧情变化、人物状态、未解决伏笔。\n"
    "2. 一次性动作、战斗过程、心理描写、气氛渲染等非持久性信息，绝对不要记录。\n"
    "3. 优先判断是否无需更新：如果本段正文没有对全局设定、人物长期状态或伏笔线索产生实质性改变，你可以完全照抄当前的运行时状态和线索，不要强行编造。\n"
    "4. 必须输出完整的最终版本：你输出的内容将直接覆盖数据库。即使只有一处小改动，你也必须把未改变的部分完整写出来，严禁使用“沿用旧内容”、“同上”、“其余不变”等占位语。\n\n"
    "【输出格式】\n"
    "- 必须包含「## 运行时状态」和「## 伏笔与线索追踪」两个二级标题\n"
    "- 直接输出内容，不要添加解释"
)

_CHAPTER_SUMMARY_SYSTEM = (
    "你是一个专业的小说章节摘要助手。\n"
    "请根据传入的章节正文，生成约 300 字的精简摘要。\n"
    "摘要只需保留：「对后续章节有影响的剧情变化、人物状态、未解决伏笔」。\n"
    "直接输出摘要文本，不要包含任何标题、解释或多余的客套话。"
)

_RUNTIME_THREADS_HEADING = "## 伏笔与线索追踪"


def parse_bible_update_response(raw: str) -> tuple[str, str]:
    """Split AI bible update response into (runtime_state, runtime_threads).

    The AI is instructed to output two ``##`` sections. If parsing fails,
    all content goes to runtime_state and runtime_threads is empty.
    """
    idx = raw.find(_RUNTIME_THREADS_HEADING)
    if idx == -1:
        return raw.strip(), ""
    state_part = raw[:idx].strip()
    threads_part = raw[idx + len(_RUNTIME_THREADS_HEADING) :].strip()
    # Remove the "## 运行时状态" heading if present at the start
    state_heading = "## 运行时状态"
    if state_part.startswith(state_heading):
        state_part = state_part[len(state_heading) :].strip()
    return state_part, threads_part


def build_bible_update_system_prompt(regenerating: bool = False) -> str:
    if regenerating:
        return _BIBLE_UPDATE_SYSTEM + _REGENERATION_GUIDANCE
    return _BIBLE_UPDATE_SYSTEM


def build_chapter_summary_system_prompt() -> str:
    return _CHAPTER_SUMMARY_SYSTEM


def build_chapter_summary_user_message(content: str) -> str:
    return f"## 章节正文\n\n{content}"


def build_bible_update_user_message(
    current_runtime_state: str,
    current_runtime_threads: str,
    content_to_check: str,
    sync_scope: str,
    previous_output: str | None = None,
    user_feedback: str | None = None,
) -> str:
    scope_label = {
        "generated_fragment": "## 待检查正文（新增片段）",
        "chapter_full": "## 待检查正文（整章）",
    }.get(sync_scope, "## 待检查正文")
    parts: list[str] = []
    if current_runtime_state.strip():
        parts.append(f"## 当前运行时状态\n\n{current_runtime_state}")
    else:
        parts.append("## 当前运行时状态\n\n（空，尚未建立）")
    if current_runtime_threads.strip():
        parts.append(f"## 当前伏笔与线索追踪\n\n{current_runtime_threads}")
    else:
        parts.append("## 当前伏笔与线索追踪\n\n（空，尚未建立）")
    parts.append(f"{scope_label}\n\n{content_to_check}")
    _append_regeneration_context(parts, previous_output, user_feedback)
    return "\n\n---\n\n".join(parts)


# --------------------------------------------------------------------------- #
#  Beat prompts (Step 7)                                                       #
# --------------------------------------------------------------------------- #

_BEAT_GENERATE_SYSTEM_TEMPLATE = (
    "你是一位番茄金番作家，正在为接下来的正文安排场景节拍和情绪钩子。\n\n"
    "节拍（Beat）是一个场景或情节的最小叙事单元，每条节拍用一句话概括将要发生的事。\n\n"
    "要求：\n"
    "- 生成指定数量的节拍，每条节拍独占一行\n"
    "- 格式：[情绪标签] 事件描述\n"
    "  例：[平静→疑惑] 主角注意到地上有一串不属于任何人的脚印\n"
    "  例：[震惊→狂喜] 彻底打脸！\n"
    "- 节拍之间应有递进的叙事逻辑和情绪起伏\n"
    "- 在爽点兑现或欲望满足的高潮环节，允许连续的纯粹爽感、打脸或生理唤醒/肉体推倒的极致宣泄\n"
    "- 不要只写情绪变化，还要写清这一拍具体让读者追什么（如期待更深的堕落、更极致的打脸）\n"
    "- 动作可以是压制、夺回、极致打脸、关系突破、打破禁忌、彻底征服或堕落\n"
    "- 最后一拍必须是钩子（悬念/反转/新信息揭露），并且最后一拍要明确勾住下一拍最想看的兑现\n"
    "- 参考已有大纲和前文，保持情节连贯\n"
    "- 只输出节拍列表，不要解释、不要前言"
    "{hook_framework}"
)


def build_beat_generate_system_prompt(
    style_prompt: str | None = None,
    plot_prompt: str | None = None,
    generation_profile: GenerationProfile | None = None,
    regenerating: bool = False,
) -> str:
    parts: list[str] = []
    if style_prompt:
        parts.append(style_prompt)
        parts.append("\n\n---\n")
    if plot_prompt:
        parts.append(
            _format_plot_prompt_pack(
                plot_prompt,
                usage="用它规划压力递进、兑现节奏和章末推动点，不得替当前项目发明或照搬样本桥段。",
            )
        )
        parts.append("\n\n---\n")
    generation_profile_block = _format_generation_profile(generation_profile)
    if generation_profile_block:
        parts.append(generation_profile_block)
        parts.append("\n\n---\n")
    hook_framework = _get_hook_framework(generation_profile)
    parts.append(_BEAT_GENERATE_SYSTEM_TEMPLATE.format(hook_framework=hook_framework))
    if regenerating:
        parts.append(_REGENERATION_GUIDANCE)
    return "\n".join(parts)


def build_beat_generate_user_message(
    text_before_cursor: str,
    outline_detail: str,
    runtime_state: str,
    runtime_threads: str,
    num_beats: int,
    length_context: str = "",
    current_chapter_context: str = "",
    previous_chapter_context: str = "",
    previous_output: str | None = None,
    user_feedback: str | None = None,
) -> str:
    """构建节拍生成的用户消息，包含已有上下文。"""
    parts: list[str] = []
    if current_chapter_context.strip():
        parts.append(f"## 当前章节\n\n{current_chapter_context}")
    if outline_detail.strip():
        parts.append(f"## 章节细纲\n\n{outline_detail}")
    if runtime_state.strip():
        parts.append(f"## 运行时状态\n\n{runtime_state}")
    if runtime_threads.strip():
        parts.append(f"## 伏笔与线索追踪\n\n{runtime_threads}")
    if previous_chapter_context.strip():
        parts.append(f"## 前序章节\n\n{previous_chapter_context}")
    # 取最后 N 字作为前文上下文
    recent = (
        text_before_cursor[-BEAT_GENERATE_CONTEXT_CHARS:]
        if len(text_before_cursor) > BEAT_GENERATE_CONTEXT_CHARS
        else text_before_cursor
    )
    if recent.strip():
        parts.append(f"## 前文（最近部分）\n\n{recent}")
    if length_context:
        parts.append(length_context)
    _append_regeneration_context(parts, previous_output, user_feedback)
    parts.append(f"\n请生成 {num_beats} 个节拍：")
    return "\n\n---\n\n".join(parts)


def _build_beat_expand_system(beat_expand_chars: int = 500, hook_framework: str = "") -> str:
    return (
        "你是一位番茄金番作家，正在根据前文和给定节拍继续落正文。\n\n"
        "要求：\n"
        f"- 按照节拍描述展开约 {beat_expand_chars} 字的叙事段落\n"
        "- 保持与前文的语感和风格一致\n"
        "- 自然衔接前文，不要重复已有内容\n"
        "- 至少包含一个五感细节（视觉/听觉/嗅觉/触觉）\n"
        "- 对话部分要有潜台词，不直接说出意图\n"
        "- 段落控制在 150 字以内，适配移动端阅读\n"
        "- 动作/战斗场景用短句加快节奏\n"
        "- 每一段都要落下可感知的读者奖励（如极致的多巴胺爽感、金钱权力的兑现、或纯粹的生理与欲望满足）\n"
        "- 允许大段甚至整章的纯粹氛围、五感描写和欲望宣泄，充分满足读者的期待感与征服欲\n"
        "- 让读者体验主角正在享受绝对的权力掌控、彻底推倒高冷角色、或享受绝对忠诚的后宫陪伴\n"
        "- 直接输出正文，不要输出节拍本身、不要解释"
        f"{hook_framework}"
    )


def build_beat_expand_system_prompt(
    style_prompt: str | None = None,
    plot_prompt: str | None = None,
    generation_profile: GenerationProfile | None = None,
    beat_expand_chars: int = 500,
    regenerating: bool = False,
) -> str:
    parts: list[str] = []
    if style_prompt:
        parts.append(style_prompt)
        parts.append("\n\n---\n")
    if plot_prompt:
        parts.append(
            _format_plot_prompt_pack(
                plot_prompt,
                usage="续写只用于防止情节跑偏和洗白，不得复制样本角色、设定、事件或桥段。",
            )
        )
        parts.append("\n\n---\n")
    generation_profile_block = _format_generation_profile(generation_profile)
    if generation_profile_block:
        parts.append(generation_profile_block)
        parts.append("\n\n---\n")
    hook_framework = _get_hook_framework(generation_profile)
    parts.append(_build_beat_expand_system(beat_expand_chars, hook_framework))
    if regenerating:
        parts.append(_REGENERATION_GUIDANCE)
    return "\n".join(parts)


def build_beat_expand_user_message(
    text_before_cursor: str,
    beat: str,
    beat_index: int,
    total_beats: int,
    preceding_beats_prose: str,
    outline_detail: str,
    runtime_state: str,
    runtime_threads: str,
    current_chapter_context: str = "",
    previous_chapter_context: str = "",
    previous_output: str | None = None,
    user_feedback: str | None = None,
) -> str:
    parts: list[str] = []
    if current_chapter_context.strip():
        parts.append(f"## 当前章节\n\n{current_chapter_context}")
    if outline_detail.strip():
        parts.append(f"## 章节细纲\n\n{outline_detail}")
    if runtime_state.strip():
        parts.append(f"## 运行时状态\n\n{runtime_state}")
    if runtime_threads.strip():
        parts.append(f"## 伏笔与线索追踪\n\n{runtime_threads}")
    if previous_chapter_context.strip():
        parts.append(f"## 前序章节\n\n{previous_chapter_context}")
    recent = (
        text_before_cursor[-BEAT_EXPAND_CONTEXT_CHARS:]
        if len(text_before_cursor) > BEAT_EXPAND_CONTEXT_CHARS
        else text_before_cursor
    )
    if recent.strip():
        parts.append(f"## 前文\n\n{recent}")
    if preceding_beats_prose.strip():
        parts.append(f"## 本轮已生成的内容\n\n{preceding_beats_prose}")
    parts.append(f"## 当前节拍（第 {beat_index + 1}/{total_beats} 拍）\n\n{beat}")
    _append_regeneration_context(parts, previous_output, user_feedback)
    return "\n\n---\n\n".join(parts)


# --------------------------------------------------------------------------- #
#  Concept generation prompts (gacha)                                          #
# --------------------------------------------------------------------------- #

_CONCEPT_GENERATE_SYSTEM_TEMPLATE = (
    "你是一位深耕网文市场（起点、番茄等平台）的资深策划编辑。\n\n"
    "你需要根据用户给出的灵感描述，产出指定数量的小说概念卡。"
    "这些概念卡必须共享同一故事主轴，是同一本书的不同包装方向，"
    "不能写成三本完全不同的小说。"
    "每个概念包含标题和一段可直接用作项目简介的简介。\n\n"
    "## 生成前的隐式判断\n"
    "在输出前，先在内部完成以下判断，但不要把判断过程写出来：\n"
    "- 主角是谁，当前最抓人的身份和处境是什么\n"
    "- 读者为什么会点进来并继续追，这本书当前的主驱动轴是什么\n"
    "- 真正能支撑点击的核心卖点是什么\n"
    "- 简介是否适合用短标签开头\n\n"
    "## 差异化规则\n"
    "所有概念卡都必须保留同一故事主轴，只能改变卖点切口与包装方式。\n"
    "差异优先体现在主角切口、局势压力、关系张力、破局手段或兑现方式。\n"
    "不要为了拉开差异，硬把同一主轴写成更大的体系、更多的势力或更高的世界层级。\n"
    "三张卡的差异必须围绕主驱动轴做不同包装，不是只换标题和设定表皮。\n"
    "建议分别优先突出以下入口：\n"
    "- 概念 1：主角身份与开局处境最抓人\n"
    "- 概念 2：机制 / 金手指 / 核心玩法最抓人\n"
    "- 概念 3：人物关系 / 对抗局面 / 情绪钩子最抓人\n\n"
    "## 标题规则\n"
    "- 标题要符合现代网文命名气质，可以短狠、反问、反差、轻俏，但不要冗长解释\n"
    "- 禁止平庸标题如「我的XXX之旅」「关于XXX这件事」\n"
    "- 标题参考气质：道诡异仙、娱乐春秋、反派：仙子哪里逃？、"
    "圣女沉沦？我的许愿系统不对劲！、让你代管宗门，怎么全成大帝了\n\n"
    "## 简介规则\n"
    "- 字数控制在 150-260 字左右，按 1-3 个自然段组织\n"
    "- 宁可短而抓人，也不要为了显得厚重而写成长简介\n"
    "- 按题材决定是否使用短标签开头；强爽文、系统文、多女主、修罗场题材可用短标签，"
    "权谋、悬疑、偏剧情型题材可直接正文开场\n"
    "- 第一段尽快交代主角是谁、正被什么局面逼住、引爆事件是什么\n"
    "- 中段把卖点落在事件、机制、关系或局势上，不要只喊口号，也不要堆设定规模\n"
    "- 结尾保留继续读的欲望，但不要写成广告标语或硬拗金句\n\n"
    "## 写法要求\n"
    "- 像小说简介，不像广告投流文案\n"
    "- 先写人和局，再写大词，不要空泛开场\n"
    "- 可以有网文味和爽点，但不要油腻、不要连续宣传腔\n"
    "- 不要连续堆砌模板反转句、排比句、四字词和宣言句\n"
    "- 不要把简介写成金句合集\n"
    "- 不要为了显得炸裂而生造宏大名词、尊号和设定术语\n"
    "- 标签如果使用，只能压缩卖点，不能替代正文\n\n"
    "## 示例学习\n"
    "以下示例仅用于学习标题气质、简介节奏与卖点组织方式。"
    "仅学习标题气质、简介节奏与卖点组织方式，"
    "不要照搬示例中的设定、身份、名词、人物关系和具体桥段。\n\n"
    "### 示例 1（优点：主角处境明确，卖点落在关系和场景上）\n"
    "### 反派：仙子哪里逃？\n"
    "【反派+多女主+日常+修罗场+不舔狗】 陈善知穿越到了一款多女主RPG游戏里，成了大反派镇国侯的纨绔短命世子。"
    "这款游戏里，绝大部分奇遇都和某个女主绑定，只要把好感刷到最高，就能拿到对应奖励。"
    "而陈善知脑海里，偏偏装着整个游戏攻略和各个女主的详细信息。\n\n"
    "为了活命，他只能比原主角更早一步下场，想尽办法把那些本不该站在自己这边的人，全都拉到自己阵营。"
    "可他越往前走，越发现这不只是刷好感那么简单，朝局、宗门、皇权和主角团的命运，早就被搅成了一锅滚油。\n\n"
    "等到原本的主角修炼有成，上门寻仇时，却只看到妹妹替陈善知剥葡萄，女剑仙给他捏腿，连高高在上的女皇都靠在他怀里。"
    "陈善知看着目眦欲裂的对方，笑得云淡风轻：抱歉，在这游戏里，修炼没用。\n\n"
    "### 示例 2（优点：机制离谱，但叙述口气自然）\n"
    "### 圣女沉沦？我的许愿系统不对劲！\n"
    "【爽文+杀伐果断+伪无敌+许愿+艺术+多红颜】 宁易宿慧觉醒，穿越到武道为尊的大周王朝，得到了【大艺术家许愿系统】。"
    "这个系统的规则很简单：只要学习艺术，就能提升武道神通境界，并得到许愿点进行许愿。"
    "问题在于，它实现愿望的方式，总带着一点不太正经的味道。\n\n"
    "他想要金钱，系统安排他碰瓷龙宫龙女；他想要顶级功法，系统直接送来要和圣女一起修的双修秘典；"
    "他说书、酿酒、吟诗、弹琴，本想混日子，却一次次把自己推到风口浪尖。"
    "在这个妖庭环伺、魔道猖獗的时代里，人人都在苦修争命，唯独他靠着一套离谱系统，把艺术玩成了通天大道。\n\n"
    "直到某一日，宁易横空出世，一拳震塌五行，翻转阴阳，所有人才终于意识到："
    "这个看似不务正业的少年，早就用最不正经的方式，走上了最不讲道理的无敌路。\n\n"
    "### 示例 3（优点：轻佻有趣，但不是搞笑文案）\n"
    "### 娱乐春秋\n"
    "现代人闯进架空异界，面对的不只是武道百家，还有一整个只知道苦修争雄的世界。"
    "别人练武求名，他却偏要用戏曲、话术、娱乐、审美和知识，把江湖、宗门乃至朝局一起搅动。"
    "这类简介的优点，不在于靠夸张词炸人，而在于主角方法论够新，语气够松，卖点仍然落在他能怎么改变这个世界。\n\n"
    "若用户灵感不含系统、多女主、修罗场、反派等元素，不得因为示例出现过就强行加入。\n\n"
    "{hook_framework}\n\n"
    "## 输出格式\n"
    "请使用 Markdown 格式输出，每个概念采用以下结构：\n"
    "### [标题]\n"
    "[简介]\n\n"
    "直接输出内容，不要添加任何其他前言或总结、也不要输出任何序号。"
)


def build_concept_generate_system_prompt(
    style_prompt: str | None = None,
    plot_prompt: str | None = None,
    generation_profile: GenerationProfile | None = None,
    regenerating: bool = False,
) -> str:
    parts: list[str] = []
    if style_prompt:
        parts.append("# Style Prompt Pack（风格约束）\n\n")
        parts.append(style_prompt.strip())
        parts.append("\n\n---\n")
    if plot_prompt:
        parts.append(
            _format_plot_prompt_pack(
                plot_prompt,
                usage=(
                    "概念生成阶段也必须应用已选 Plot/Style Profile；"
                    "标题和简介要体现 Plot Pack 的主驱动轴、读者追读问题和角色功能位。"
                ),
            )
        )
        parts.append("\n\n---\n")
    if generation_profile:
        parts.append(
            "# Generation Profile（运行时生成约束）\n\n"
            f"target_market: {generation_profile.target_market}\n"
            f"genre_mother: {generation_profile.genre_mother}\n"
            f"desire_overlays: {', '.join(generation_profile.desire_overlays) or 'none'}\n"
            f"intensity_level: {generation_profile.intensity_level}\n"
            f"pov_mode: {generation_profile.pov_mode}\n"
            f"morality_axis: {generation_profile.morality_axis}\n"
            f"pace_density: {generation_profile.pace_density}\n\n"
            "这些字段是显式创作目标，不要弱化。"
        )
        parts.append("\n\n---\n")
    hook_framework = _get_hook_framework(generation_profile)
    parts.append(_CONCEPT_GENERATE_SYSTEM_TEMPLATE.format(hook_framework=hook_framework))
    if regenerating:
        parts.append(_REGENERATION_GUIDANCE)
    return "\n".join(parts)


def build_concept_generate_user_message(
    inspiration: str,
    count: int,
    previous_output: str | None = None,
    user_feedback: str | None = None,
) -> str:
    parts: list[str] = [f"请根据以下灵感描述生成 {count} 个小说概念：\n\n{inspiration}"]
    _append_regeneration_context(parts, previous_output, user_feedback)
    return "\n\n---\n\n".join(parts)
