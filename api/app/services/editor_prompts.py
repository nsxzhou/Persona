"""Zen Editor 相关的提示词模板。

包含区块 AI 生成、改写、节拍等各类提示词构建函数。
"""

from __future__ import annotations

from app.core.bible_fields import BIBLE_FIELD_KEYS, BIBLE_FIELD_LABELS

BEAT_GENERATE_CONTEXT_CHARS = 2000
BEAT_EXPAND_CONTEXT_CHARS = 1500

# --------------------------------------------------------------------------- #
#  Section generation prompts (Step 2)                                         #
# --------------------------------------------------------------------------- #

_SECTION_META: dict[str, dict[str, str]] = {
    "world_building": {
        "label": "世界观设定",
        "instruction": (
            "请基于灵感概述和已有上下文，构建这部小说的世界观设定。\n\n"
            "必须覆盖以下六个维度，每个维度用二级标题分隔：\n"
            "1. **时代背景与核心法则** — 这个世界运行的底层规则（灵气/科技/超能力等），"
            "决定一切设定的根基\n"
            "2. **地理与空间结构** — 主要地图区域、势力版图、关键地标；"
            "要有「地图换挡」意识（从小地图到大地图的扩展路径）\n"
            "3. **势力与阵营** — 至少 3 个互相制衡的势力，"
            "写出名称、实力位阶、核心利益和潜在冲突\n"
            "4. **力量/修炼体系** — 等级划分（至少 6 级）、突破条件、"
            "战力表现差异、主角金手指在体系中的定位\n"
            "5. **社会结构与经济** — 货币体系、阶层分化、普通人的生存状态"
            "（读者需要通过普通人的视角感受世界的真实感）\n"
            "6. **历史大事件** — 2-3 个影响当前局势的关键历史节点\n\n"
            "一致性规则：\n"
            "- 力量体系必须影响社会结构（如：修炼者能飞，就不需要修路）\n"
            "- 经济必须与力量等级挂钩（强者如何获取资源）\n"
            "- 地理格局必须服务于主角的活动范围扩张路径"
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
    "story_bible": {
        "label": "故事圣经补充",
        "instruction": (
            "请基于已有上下文，生成一份初始的故事圣经补充材料。\n\n"
            "必须包含以下部分：\n"
            "1. **时间线** — 关键事件按时序排列\n"
            "2. **活跃伏笔** — 尚未回收的悬念/暗示/线索，每条标注：\n"
            "   - 类型（设定伏笔/人物伏笔/道具伏笔）\n"
            "   - 埋设位置（大约在哪里出现）\n"
            "   - 重要程度（核心线/支线）\n"
            "3. **已回收线索** — 已完成回收的伏笔\n"
            "4. **设定约束备忘** — 已确立的硬性设定规则"
            "（如某角色的能力限制、某地点的特殊规则等），"
            "防止后续写作出现自相矛盾"
        ),
    },
}

VALID_SECTIONS = frozenset(_SECTION_META.keys())


def build_section_system_prompt(section: str, style_prompt: str | None = None) -> str:
    """构建区块生成的系统提示词。"""
    meta = _SECTION_META[section]
    parts: list[str] = []
    if style_prompt:
        parts.append(style_prompt)
        parts.append("\n\n---\n")
    parts.append(
        f"你是一位资深的小说策划编辑，正在帮助作者构建「{meta['label']}」。\n"
        f"{meta['instruction']}\n\n"
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
#  Bible update prompts (Step 6)                                               #
# --------------------------------------------------------------------------- #

_BIBLE_UPDATE_SYSTEM = (
    "你是一位小说项目的设定维护助手。\n"
    "你的职责是根据最新生成的正文内容，更新故事圣经的「补充」部分。\n\n"
    "故事圣经补充包含四个部分：\n"
    "1. **时间线** — 关键事件按时序排列\n"
    "2. **活跃伏笔** — 尚未回收的悬念，每条标注类型"
    "（设定/人物/道具）和重要程度（核心/支线）\n"
    "3. **已回收线索** — 已完成回收的伏笔，标注回收位置\n"
    "4. **设定约束备忘** — 已确立的硬性设定规则\n\n"
    "更新规则：\n"
    "- 保留原有内容中仍然有效的信息\n"
    "- 根据新正文追加新出现的事件、角色、伏笔\n"
    "- 如果新正文回收了某条伏笔，将其从「活跃伏笔」移至「已回收线索」\n"
    "- 如果新正文确立了新的硬性设定规则，添加到「设定约束备忘」\n"
    "- 输出完整的更新后故事圣经补充，使用 Markdown 格式\n"
    "- 直接输出内容，不要添加解释"
)


def build_bible_update_system_prompt() -> str:
    return _BIBLE_UPDATE_SYSTEM


def build_bible_update_user_message(current_bible: str, new_content: str) -> str:
    parts: list[str] = []
    if current_bible.strip():
        parts.append(f"## 当前故事圣经补充\n\n{current_bible}")
    else:
        parts.append("## 当前故事圣经补充\n\n（空，尚未建立）")
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
    story_bible: str,
    num_beats: int,
) -> str:
    parts: list[str] = []
    if outline_detail.strip():
        parts.append(f"## 章节细纲\n\n{outline_detail}")
    if story_bible.strip():
        parts.append(f"## 故事圣经\n\n{story_bible}")
    # 取最后 N 字作为前文上下文
    recent = text_before_cursor[-BEAT_GENERATE_CONTEXT_CHARS:] if len(text_before_cursor) > BEAT_GENERATE_CONTEXT_CHARS else text_before_cursor
    if recent.strip():
        parts.append(f"## 前文（最近部分）\n\n{recent}")
    parts.append(f"\n请生成 {num_beats} 个节拍：")
    return "\n\n---\n\n".join(parts)


_BEAT_EXPAND_SYSTEM = (
    "你是一位小说执笔者，正在根据给定的节拍展开正文。\n\n"
    "要求：\n"
    "- 按照节拍描述展开约 500 字的叙事段落\n"
    "- 保持与前文的语感和风格一致\n"
    "- 自然衔接前文，不要重复已有内容\n"
    "- 至少包含一个五感细节（视觉/听觉/嗅觉/触觉）\n"
    "- 对话部分要有潜台词，不直接说出意图\n"
    "- 段落控制在 150 字以内，适配移动端阅读\n"
    "- 动作/战斗场景用短句加快节奏\n"
    "- 直接输出正文，不要输出节拍本身、不要解释"
)


def build_beat_expand_system_prompt(style_prompt: str | None = None) -> str:
    parts: list[str] = []
    if style_prompt:
        parts.append(style_prompt)
        parts.append("\n\n---\n")
    parts.append(_BEAT_EXPAND_SYSTEM)
    return "\n".join(parts)


def build_beat_expand_user_message(
    text_before_cursor: str,
    beat: str,
    beat_index: int,
    total_beats: int,
    preceding_beats_prose: str,
    outline_detail: str,
    story_bible: str,
) -> str:
    parts: list[str] = []
    if outline_detail.strip():
        parts.append(f"## 章节细纲\n\n{outline_detail}")
    if story_bible.strip():
        parts.append(f"## 故事圣经\n\n{story_bible}")
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
