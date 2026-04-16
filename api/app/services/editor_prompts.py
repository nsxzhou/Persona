"""Zen Editor 相关的提示词模板。

包含区块 AI 生成、改写、节拍等各类提示词构建函数。
"""

from __future__ import annotations

from app.core.bible_fields import BIBLE_FIELD_KEYS, BIBLE_FIELD_LABELS
from app.core.length_presets import LengthPresetKey

BEAT_GENERATE_CONTEXT_CHARS = 2000
BEAT_EXPAND_CONTEXT_CHARS = 1500

# --------------------------------------------------------------------------- #
#  Length-preset-aware section instructions                                     #
# --------------------------------------------------------------------------- #

# 按篇幅预设区分的大纲指令
_OUTLINE_MASTER_INSTRUCTIONS: dict[str, str] = {
    "short": (
        "请基于灵感概述、世界观、角色设定和已有上下文，设计这部小说的总纲。\n\n"
        "以「三幕结构」规划，每幕用二级标题，包含：\n"
        "- **幕名称与字数范围**（如「第一幕：建置 0-3万字」）\n"
        "- **核心场景**（不超过 3 个主要场景）\n"
        "- **核心冲突与转折点**\n"
        "- **主角状态变化**\n"
        "- **幕末钩子**（驱动读者继续的悬念或反转）\n\n"
        "全局节奏要求：\n"
        "- 短篇节奏紧凑，每 1-2 万字一个重大转折\n"
        "- 开篇 5000 字内必须建立核心冲突\n"
        "- 全篇围绕一个核心矛盾展开，不开支线\n"
        "- 结尾必须有明确的情感落点或意义揭示"
    ),
    "medium": (
        "请基于灵感概述、世界观、角色设定和已有上下文，设计这部小说的总纲。\n\n"
        "以「阶段」为单位规划（建议 3-5 个阶段），每个阶段用二级标题，包含：\n"
        "- **阶段名称与字数范围**（如「序章期 0-5万字」）\n"
        "- **核心地图/场景**\n"
        "- **阶段核心对手**（实力定位和冲突类型）\n"
        "- **主角力量等级跨度**（本阶段起点 → 终点）\n"
        "- **核心爽点事件**（至少 1-2 个）\n"
        "- **阶段末钩子**\n\n"
        "全局节奏要求：\n"
        "- 遵循「小高潮-缓冲-大高潮」循环\n"
        "- 每 3-5 万字至少一个重大事件\n"
        "- 开篇 1 万字内建立核心冲突和角色魅力\n"
        "- 每个阶段结束必须有一个让读者无法放下的钩子"
    ),
    "long": (
        "请基于灵感概述、世界观、角色设定和已有上下文，设计这部小说的总纲。\n\n"
        "以「地图/阶段」为单位规划，每个阶段用二级标题，包含：\n"
        "- **阶段名称与字数范围**（如「起步期 0-15万字」）\n"
        "- **核心地图/场景**（体现世界逐步展开的「地图换挡」）\n"
        "- **阶段 Boss/核心对手**（实力定位和冲突类型）\n"
        "- **主角力量等级跨度**（本阶段起点 → 终点）\n"
        "- **核心爽点事件**（至少 2 个打脸/逆袭/突破）\n"
        "- **阶段末钩子**（驱动读者继续的悬念或反转）\n\n"
        "全局节奏要求：\n"
        "- 遵循「小高潮-缓冲-大高潮」循环\n"
        "- 每 3-5 万字至少一个重大事件\n"
        "- 前 30 万字（追读养成期）节奏偏快，密集爽点\n"
        "- 每个阶段结束必须有一个让读者无法放下的钩子"
    ),
}

_OUTLINE_DETAIL_INSTRUCTIONS: dict[str, str] = {
    "short": (
        "请基于总纲和已有上下文，展开章节细纲。\n"
        "目标篇幅 5-15 万字，建议 8-20 章。\n\n"
        "每章必须包含：\n"
        "- **章节标题**\n"
        "- **核心事件**（1-2 句话概括）\n"
        "- **情绪走向**（如「平静 → 疑惑 → 震惊 → 愤怒」）\n"
        "- **章末钩子**（必填！每章结尾必须有悬念或爆点）\n\n"
        "节奏规则：\n"
        "- 短篇不设分卷，直接列出章节\n"
        "- 每 3-5 章安排一个转折\n"
        "- 最后 2-3 章进入收束，回收伏笔，不要开新线"
    ),
    "medium": (
        "请基于总纲和已有上下文，展开分卷结构和章节细纲。\n"
        "目标篇幅 15-50 万字，建议 2-4 卷。\n\n"
        "每卷用二级标题标注卷名和主题，其下列出各章节。\n"
        "每章必须包含：\n"
        "- **章节标题**\n"
        "- **核心事件**（2-3 句话概括）\n"
        "- **情绪走向**（如「平静 → 疑惑 → 震惊 → 愤怒」）\n"
        "- **章末钩子**（必填！每章结尾必须有悬念或爆点）\n\n"
        "节奏规则：\n"
        "- 同一卷内的章节情绪应有起伏\n"
        "- 每 3-5 章安排一个小高潮，每卷末安排大高潮\n"
        "- 最后一卷需安排收束，回收主要伏笔"
    ),
    "long": (
        "请基于总纲和已有上下文，展开分卷结构和章节细纲。\n\n"
        "每卷用二级标题标注卷名和主题，其下列出各章节。\n"
        "每章必须包含：\n"
        "- **章节标题**\n"
        "- **核心事件**（2-3 句话概括）\n"
        "- **情绪走向**（如「平静 → 疑惑 → 震惊 → 愤怒」）\n"
        "- **章末钩子**（必填！每章结尾必须有一个让读者想翻下一章的悬念或爆点）\n\n"
        "节奏规则：\n"
        "- 同一卷内的章节情绪应有起伏，避免连续多章同一情绪\n"
        "- 开头和结尾的情绪尽量形成反差（喜→悲，松→紧）\n"
        "- 每 3-5 章安排一个小高潮，每卷末安排大高潮"
    ),
}

# 按篇幅追加的世界观/角色补充提示
_WORLD_BUILDING_SUFFIX: dict[str, str] = {
    "short": (
        "\n\n篇幅适配提示：\n"
        "- 这是一部短篇小说（5-15万字），只保留会直接进入剧情的必要设定\n"
        "- 优先写清压迫、规则和开篇冲突，不要扩写世界百科\n"
        "- 可选模块从严取舍，能不写就不写"
    ),
    "medium": (
        "\n\n篇幅适配提示：\n"
        "- 这是一部中篇小说（15-50万字），可以适度补充主要势力或关键前史\n"
        "- 仍以主线冲突为中心，不要因为篇幅更长就补全一整套体系"
    ),
    "long": (
        "\n\n篇幅适配提示：\n"
        "- 这是一部长篇小说，可在主线确实需要时逐步展开势力、空间与前史\n"
        "- 即使是长篇，也不要预支后期暂时用不到的设定"
    ),
}

_CHARACTERS_SUFFIX: dict[str, str] = {
    "short": (
        "\n\n篇幅适配提示：\n"
        "- 这是一部短篇小说（5-15万字），角色精简\n"
        "- 重要配角 1-2 个即可\n"
        "- 阶段性反派可以与全书反派合一\n"
        "- 角色设计聚焦核心冲突，不要过多铺展"
    ),
    "medium": (
        "\n\n篇幅适配提示：\n"
        "- 这是一部中篇小说（15-50万字），角色数量适中\n"
        "- 重要配角 2-3 个\n"
        "- 可以有层次更丰富的角色关系网"
    ),
    "long": "",  # 长篇保持原样
}

# --------------------------------------------------------------------------- #
#  Section generation prompts (Step 2)                                         #
# --------------------------------------------------------------------------- #

_SECTION_META: dict[str, dict[str, str]] = {
    "world_building": {
        "label": "世界观设定",
        "instruction": (
            "请基于灵感概述和已有上下文，生成一份足以支撑人物、冲突和前期展开的必要设定。\n\n"
            "生成前先做隐式判断，不要把判断过程写出来：\n"
            "1. 先判断这部作品更接近哪种题材气质，以及超自然设定是显性、隐性还是不存在\n"
            "2. 再判断哪些设定模块对当前故事真正必要\n"
            "3. 只保留当前故事真正需要的模块，不要为了显得完整而补完世界\n\n"
            "默认必须回答以下三个核心问题，每个问题用二级标题分隔：\n"
            "1. **时代与秩序** — 这个世界的生活逻辑、权力结构、身份壁垒或社会规则是什么；"
            "重点写人物如何被环境塑形\n"
            "2. **当前局势与核心冲突土壤** — 故事为什么会在此刻开始，"
            "什么裂缝、旧案、失衡或压力正在逼近爆点\n"
            "3. **主角受限规则** — 什么规则、禁令、身份限制、资源门槛或秘密，"
            "会卡住主角并逼他做出选择\n\n"
            "仅在确有需要时，才补充下列可选模块：\n"
            "- **隐秘规则/禁忌**：仅当设定确实依赖超自然、禁术、异常机制，"
            "或少数人掌握的秘密规则\n"
            "- **主要势力**：仅当主线存在真实的多方博弈，而不是单一权力压迫\n"
            "- **关键前史**：仅当过去事件直接塑造当前冲突\n"
            "- **活动空间与扩展方向**：仅当故事确有跨区域行动、征伐、迁徙或地图扩张需求\n"
            "- **资源与利益流动**：仅当资源争夺是主线驱动力\n\n"
            "反过度生成约束：\n"
            "- 历史、权谋、现实、悬疑等题材，不要默认生成公开修炼体系或全民力量系统\n"
            "- 如果特殊规则只掌握在极少数人手里，不要把它写成社会公开常识\n"
            "- 少数人掌握的异常规则，不要包装成全民通用系统\n"
            "- 资源争夺并非主线时，不要专门发明货币、修炼材料、交易媒介\n"
            "- 不要发明暂时不会进入剧情的设定\n"
            "- 不要为了显得完整而补完世界\n"
            "- 优先写会真实影响人物选择和剧情推进的规则，而不是看上去宏大的设定"
        ),
    },
    "characters": {
        "label": "角色设定",
        "instruction": (
            "请基于灵感概述、世界观设定和已有上下文，设计这部小说的核心角色。\n\n"
            "## 主角设计\n"
            "- **核心标签**：用 3 个短语概括（如「隐忍型/扮猪吃虎/重情重义」）\n"
            "- **金手指定位**：是什么、如何获得、成长路线\n"
            "- **角色弧光**：出场状态 → 核心转折 → 最终形态\n"
            "- **反差设计**：至少一个与主要人设反差的特质"
            "（如：冷面无情但对小动物温柔）\n"
            "- **决策逻辑**：面对利益、情感、危险时的行为模式\n\n"
            "## 重要配角（至少 2 个）\n"
            "每个配角需要：\n"
            "- 与主角的关系定位（对手/导师/队友/潜在背叛者）\n"
            "- 独立动机（不是为主角而存在，有自己的目标）\n"
            "- 记忆点（一个让读者记住的外在特征或口头禅）\n\n"
            "## 阶段性反派（至少 1 个）\n"
            "- 行为逻辑合理（不能是单纯的「坏」）\n"
            "- 实力定位明确（当前阶段 Boss / 全书大 Boss）\n"
            "- 与主角的冲突核心（资源争夺/理念对立/私人恩怨）\n\n"
            "每个角色用二级标题分隔，内部用结构化列表。"
        ),
    },
    "outline_master": {
        "label": "总纲",
        "instruction": (
            "请基于灵感概述、世界观、角色设定和已有上下文，设计这部小说的总纲。\n\n"
            "以「地图/阶段」为单位规划，每个阶段用二级标题，包含：\n"
            "- **阶段名称与字数范围**（如「起步期 0-15万字」）\n"
            "- **核心地图/场景**（体现世界逐步展开的「地图换挡」）\n"
            "- **阶段 Boss/核心对手**（实力定位和冲突类型）\n"
            "- **主角力量等级跨度**（本阶段起点 → 终点）\n"
            "- **核心爽点事件**（至少 2 个打脸/逆袭/突破）\n"
            "- **阶段末钩子**（驱动读者继续的悬念或反转）\n\n"
            "全局节奏要求：\n"
            "- 遵循「小高潮-缓冲-大高潮」循环\n"
            "- 每 3-5 万字至少一个重大事件\n"
            "- 前 30 万字（追读养成期）节奏偏快，密集爽点\n"
            "- 每个阶段结束必须有一个让读者无法放下的钩子"
        ),
    },
    "outline_detail": {
        "label": "分卷与章节细纲",
        "instruction": (
            "请基于总纲和已有上下文，展开分卷结构和章节细纲。\n\n"
            "每卷用二级标题标注卷名和主题，其下列出各章节。\n"
            "每章必须包含：\n"
            "- **章节标题**\n"
            "- **核心事件**（2-3 句话概括）\n"
            "- **情绪走向**（如「平静 → 疑惑 → 震惊 → 愤怒」）\n"
            "- **章末钩子**（必填！每章结尾必须有一个让读者想翻下一章的悬念或爆点）\n\n"
            "节奏规则：\n"
            "- 同一卷内的章节情绪应有起伏，避免连续多章同一情绪\n"
            "- 开头和结尾的情绪尽量形成反差（喜→悲，松→紧）\n"
            "- 每 3-5 章安排一个小高潮，每卷末安排大高潮"
        ),
    },
    "runtime_state": {
        "label": "运行时状态",
        "instruction": (
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
        "instruction": (
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
    length_preset: LengthPresetKey = "long",
) -> str:
    """构建区块生成的系统提示词（篇幅感知）。"""
    meta = _SECTION_META[section]

    # 按 preset 选择 instruction 变体
    if section == "outline_master":
        instruction = _OUTLINE_MASTER_INSTRUCTIONS.get(
            length_preset, _OUTLINE_MASTER_INSTRUCTIONS["long"]
        )
    elif section == "outline_detail":
        instruction = _OUTLINE_DETAIL_INSTRUCTIONS.get(
            length_preset, _OUTLINE_DETAIL_INSTRUCTIONS["long"]
        )
    else:
        instruction = meta["instruction"]
        # 为世界观和角色追加篇幅提示
        if section == "world_building":
            instruction += _WORLD_BUILDING_SUFFIX.get(length_preset, "")
        elif section == "characters":
            instruction += _CHARACTERS_SUFFIX.get(length_preset, "")

    parts: list[str] = []
    if style_prompt:
        parts.append(style_prompt)
        parts.append("\n\n---\n")
    role_prefix = (
        "你是一位只保留必要设定的小说策划编辑"
        if section == "world_building"
        else "你是一位资深的小说策划编辑"
    )
    parts.append(
        f"{role_prefix}，正在帮助作者构建「{meta['label']}」。\n"
        f"{instruction}\n\n"
        "输出要求：\n"
        "- 使用 Markdown 格式，标题层级清晰\n"
        "- 内容丰富具体，避免空泛概括\n"
        "- 直接输出内容，不要添加任何解释性前言或总结"
    )
    return "\n".join(parts)


def build_section_user_message(section: str, context: dict[str, str]) -> str:
    """构建区块生成的用户消息，包含已有上下文。"""
    parts: list[str] = []
    for key in BIBLE_FIELD_KEYS:
        if key == section:
            continue
        text = context.get(key, "").strip()
        if text:
            label = BIBLE_FIELD_LABELS[key]
            parts.append(f"## {label}\n\n{text}")

    if parts:
        return "以下是当前已有的创作设定：\n\n" + "\n\n---\n\n".join(parts)
    return "（暂无其他已有设定，请基于你的创意自由发挥）"


# --------------------------------------------------------------------------- #
#  Volume-level generation prompts                                             #
# --------------------------------------------------------------------------- #

_VOLUME_GENERATE_INSTRUCTIONS: dict[str, str] = {
    "short": (
        "请基于总纲，设计三幕结构。\n\n"
        "只输出幕级结构，不要输出章节。格式要求：\n"
        "每幕用二级标题（## ），紧跟引用行（> ）标注主题和字数范围。\n\n"
        "示例格式：\n"
        "## 第一幕：建置\n"
        "> 主题：故事起点 | 字数范围：0-3万字\n\n"
        "目标篇幅：5-15 万字，建议 3 幕。"
    ),
    "medium": (
        "请基于总纲，设计分卷结构。\n\n"
        "只输出卷级结构，不要输出章节。格式要求：\n"
        "每卷用二级标题（## ），紧跟引用行（> ）标注主题和字数范围。\n\n"
        "示例格式：\n"
        "## 第一卷：卷名\n"
        "> 主题：xxx | 字数范围：0-10万字\n\n"
        "目标篇幅：15-50 万字，建议 2-4 卷。"
    ),
    "long": (
        "请基于总纲，设计分卷结构。\n\n"
        "只输出卷级结构，不要输出章节。格式要求：\n"
        "每卷用二级标题（## ），紧跟引用行（> ）标注主题和字数范围。\n\n"
        "示例格式：\n"
        "## 第一卷：卷名\n"
        "> 主题：xxx | 字数范围：0-15万字\n\n"
        "根据总纲中的阶段划分来确定卷数。"
    ),
}


def build_volume_generate_system_prompt(
    length_preset: LengthPresetKey = "long",
    style_prompt: str | None = None,
) -> str:
    """构建卷级结构生成的系统提示词。"""
    instruction = _VOLUME_GENERATE_INSTRUCTIONS.get(
        length_preset, _VOLUME_GENERATE_INSTRUCTIONS["long"]
    )
    parts: list[str] = []
    if style_prompt:
        parts.append(style_prompt)
        parts.append("\n\n---\n")
    parts.append(
        "你是一位资深的小说策划编辑，正在帮助作者规划分卷结构。\n\n"
        f"{instruction}\n\n"
        "输出要求：\n"
        "- 使用 Markdown 格式\n"
        "- 只输出分卷结构，不要输出任何章节内容\n"
        "- 直接输出内容，不要添加解释性前言或总结"
    )
    return "\n".join(parts)


def build_volume_generate_user_message(outline_master: str) -> str:
    """构建卷级结构生成的用户消息。"""
    if outline_master.strip():
        return f"## 总纲\n\n{outline_master}"
    return "（总纲尚未填写，请基于创意自由规划分卷）"


_VOLUME_CHAPTERS_SYSTEM = (
    "你是一位资深的小说策划编辑，正在帮助作者展开某一卷的章节细纲。\n\n"
    "为指定的卷设计章节。每章用三级标题（### ），格式如下：\n\n"
    "### 第 N 章：章名\n"
    "- **核心事件**：一句话概括\n"
    "- **情绪走向**：如「平静 → 震惊 → 愤怒」\n"
    "- **章末钩子**：驱动读者继续阅读的悬念或反转\n\n"
    "要求：\n"
    "- 章节之间情绪有起伏，不要连续同一情绪\n"
    "- 每章末必须有钩子\n"
    "- 参考已有的前几卷章节，保持情节连贯\n"
    "- 直接输出章节列表，不要输出卷标题，不要添加解释"
)


def build_volume_chapters_system_prompt(style_prompt: str | None = None) -> str:
    """构建单卷章节生成的系统提示词。"""
    parts: list[str] = []
    if style_prompt:
        parts.append(style_prompt)
        parts.append("\n\n---\n")
    parts.append(_VOLUME_CHAPTERS_SYSTEM)
    return "\n".join(parts)


def build_volume_chapters_user_message(
    outline_master: str,
    volume_title: str,
    volume_meta: str,
    preceding_chapters_summary: str,
) -> str:
    """构建单卷章节生成的用户消息。"""
    parts: list[str] = []
    if outline_master.strip():
        parts.append(f"## 总纲\n\n{outline_master}")
    parts.append(f"## 当前卷\n\n**{volume_title}**\n{volume_meta}")
    if preceding_chapters_summary.strip():
        parts.append(f"## 前几卷已有章节（参考，保持连贯）\n\n{preceding_chapters_summary}")
    parts.append("请为当前卷设计章节细纲：")
    return "\n\n---\n\n".join(parts)


# --------------------------------------------------------------------------- #
#  Bible update prompts (Step 6)                                               #
# --------------------------------------------------------------------------- #

_BIBLE_UPDATE_SYSTEM = (
    "你是一位小说项目的设定维护助手。\n"
    "你的职责是根据最新生成的正文内容，更新两部分运行时追踪文档。\n\n"
    "你必须输出以下两个区块，用对应的二级标题分隔：\n\n"
    "## 运行时状态\n"
    "包含三个部分：\n"
    "1. **时间线** — 关键事件按时序排列\n"
    "2. **角色当前状态** — 角色的状态变化（伤病、关系变化、新出场角色）\n"
    "3. **新揭示世界规则** — 随剧情揭示的世界设定\n\n"
    "## 伏笔与线索追踪\n"
    "包含三个部分：\n"
    "1. **活跃伏笔** — 尚未回收的悬念，每条标注类型"
    "（设定/人物/道具）和重要程度（核心/支线）\n"
    "2. **已回收线索** — 已完成回收的伏笔，标注回收位置\n"
    "3. **设定约束备忘** — 已确立的硬性设定规则\n\n"
    "更新规则：\n"
    "- 保留原有内容中仍然有效的信息\n"
    "- 根据新正文追加新出现的事件、角色、伏笔\n"
    "- 如果新正文回收了某条伏笔，将其从「活跃伏笔」移至「已回收线索」\n"
    "- 如果新正文确立了新的硬性设定规则，添加到「设定约束备忘」\n"
    "- 输出完整的更新后内容，使用 Markdown 格式\n"
    "- 必须包含「## 运行时状态」和「## 伏笔与线索追踪」两个二级标题\n"
    "- 直接输出内容，不要添加解释"
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
    threads_part = raw[idx + len(_RUNTIME_THREADS_HEADING):].strip()
    # Remove the "## 运行时状态" heading if present at the start
    state_heading = "## 运行时状态"
    if state_part.startswith(state_heading):
        state_part = state_part[len(state_heading):].strip()
    return state_part, threads_part


def build_bible_update_system_prompt() -> str:
    return _BIBLE_UPDATE_SYSTEM


def build_bible_update_user_message(
    current_runtime_state: str,
    current_runtime_threads: str,
    new_content: str,
) -> str:
    parts: list[str] = []
    if current_runtime_state.strip():
        parts.append(f"## 当前运行时状态\n\n{current_runtime_state}")
    else:
        parts.append("## 当前运行时状态\n\n（空，尚未建立）")
    if current_runtime_threads.strip():
        parts.append(f"## 当前伏笔与线索追踪\n\n{current_runtime_threads}")
    else:
        parts.append("## 当前伏笔与线索追踪\n\n（空，尚未建立）")
    parts.append(f"## 本次新生成的正文\n\n{new_content}")
    return "\n\n---\n\n".join(parts)


# --------------------------------------------------------------------------- #
#  Beat prompts (Step 7)                                                       #
# --------------------------------------------------------------------------- #

_BEAT_GENERATE_SYSTEM = (
    "你是一位资深的小说策划编辑，正在帮助作者规划接下来的写作节拍。\n\n"
    "节拍（Beat）是一个场景或情节的最小叙事单元，每条节拍用一句话概括将要发生的事。\n\n"
    "要求：\n"
    "- 生成指定数量的节拍，每条节拍独占一行\n"
    "- 格式：[情绪标签] 事件描述\n"
    "  例：[平静→疑惑] 主角注意到地上有一串不属于任何人的脚印\n"
    "  例：[震惊→愤怒] 真相揭露——师兄就是幕后黑手\n"
    "- 节拍之间应有递进的叙事逻辑和情绪起伏\n"
    "- 不能连续 3 拍以上保持同一情绪基调\n"
    "- 最后一拍必须是钩子（悬念/反转/新信息揭露）\n"
    "- 参考已有大纲和前文，保持情节连贯\n"
    "- 只输出节拍列表，不要解释、不要前言"
)


def build_beat_generate_system_prompt(style_prompt: str | None = None) -> str:
    parts: list[str] = []
    if style_prompt:
        parts.append(style_prompt)
        parts.append("\n\n---\n")
    parts.append(_BEAT_GENERATE_SYSTEM)
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
    recent = text_before_cursor[-BEAT_GENERATE_CONTEXT_CHARS:] if len(text_before_cursor) > BEAT_GENERATE_CONTEXT_CHARS else text_before_cursor
    if recent.strip():
        parts.append(f"## 前文（最近部分）\n\n{recent}")
    if length_context:
        parts.append(length_context)
    parts.append(f"\n请生成 {num_beats} 个节拍：")
    return "\n\n---\n\n".join(parts)


def _build_beat_expand_system(beat_expand_chars: int = 500) -> str:
    return (
        "你是一位小说执笔者，正在根据给定的节拍展开正文。\n\n"
        "要求：\n"
        f"- 按照节拍描述展开约 {beat_expand_chars} 字的叙事段落\n"
        "- 保持与前文的语感和风格一致\n"
        "- 自然衔接前文，不要重复已有内容\n"
        "- 至少包含一个五感细节（视觉/听觉/嗅觉/触觉）\n"
        "- 对话部分要有潜台词，不直接说出意图\n"
        "- 段落控制在 150 字以内，适配移动端阅读\n"
        "- 动作/战斗场景用短句加快节奏\n"
        "- 直接输出正文，不要输出节拍本身、不要解释"
    )


def build_beat_expand_system_prompt(
    style_prompt: str | None = None,
    beat_expand_chars: int = 500,
) -> str:
    parts: list[str] = []
    if style_prompt:
        parts.append(style_prompt)
        parts.append("\n\n---\n")
    parts.append(_build_beat_expand_system(beat_expand_chars))
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
    recent = text_before_cursor[-BEAT_EXPAND_CONTEXT_CHARS:] if len(text_before_cursor) > BEAT_EXPAND_CONTEXT_CHARS else text_before_cursor
    if recent.strip():
        parts.append(f"## 前文\n\n{recent}")
    if preceding_beats_prose.strip():
        parts.append(f"## 本轮已生成的内容\n\n{preceding_beats_prose}")
    parts.append(f"## 当前节拍（第 {beat_index + 1}/{total_beats} 拍）\n\n{beat}")
    return "\n\n---\n\n".join(parts)


# --------------------------------------------------------------------------- #
#  Concept generation prompts (gacha)                                          #
# --------------------------------------------------------------------------- #

_CONCEPT_GENERATE_SYSTEM = (
    "你是一位深耕男频网文市场的资深策划编辑。\n\n"
    "你需要根据用户的灵感描述，生成指定数量的小说概念。"
    "每个概念包含标题和一句话简介。\n\n"
    "## 差异化策略\n"
    "你生成的概念必须分别采用不同的策略方向，确保风格差异最大化：\n"
    "- 概念 1 采用「爽文流」：突出金手指/系统 + 打脸逆袭 + 快感承诺\n"
    "- 概念 2 采用「悬念流」：突出谜团/身份反转 + 命运暗线 + 好奇心驱动\n"
    "- 概念 3 采用「人设流」：突出角色反差萌/独特身份 + 情感张力 + 代入感\n"
    "- 若需生成更多，自行组合以上策略或引入新切入角度\n\n"
    "## 标题规则\n"
    "- 不超过 10 个汉字\n"
    "- 好标题示例：「全球进化：从一条狗开始」「我在末世捡属性」「被退婚后我觉醒了SSS天赋」\n"
    "- 禁止平庸标题如「我的XXX之旅」「关于XXX这件事」\n\n"
    "## 简介规则\n"
    "- 不超过 50 个汉字\n"
    "- 第一句必须包含冲突或异常（黄金三行法则）\n"
    "- 必须暗示核心卖点（金手指/悬念/人设）\n"
    "- 结尾留悬念，不揭示结局\n\n"
    "## 输出格式\n"
    "请使用 Markdown 格式输出，每个概念采用以下结构：\n"
    "### [标题]\n"
    "[简介]\n\n"
    "示例：\n"
    "### 全球进化：从一条狗开始\n"
    "末日降临，别人觉醒异能，我却变成了一条狗……\n\n"
    "直接输出内容，不要添加任何其他前言或总结、也不要输出任何序号。"
)


def build_concept_generate_system_prompt() -> str:
    return _CONCEPT_GENERATE_SYSTEM


def build_concept_generate_user_message(inspiration: str, count: int) -> str:
    return f"请根据以下灵感描述生成 {count} 个小说概念：\n\n{inspiration}"
