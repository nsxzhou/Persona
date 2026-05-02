from __future__ import annotations

from app.core.length_presets import LengthPresetKey
from app.prompts.common import REGENERATION_GUIDANCE, append_regeneration_context
from app.prompts.novel_shared import (
    MALE_COMMERCIAL_ENGINE,
    append_profile_blocks,
    append_soft_length_hint,
    build_volume_planning_budget_hint,
    get_hook_framework,
)
from app.prompts.section_context import build_section_user_message
from app.schemas.prompt_profiles import GenerationProfile

_OUTLINE_DETAIL_INSTRUCTION_TEMPLATE = (
    "从总纲和已有上下文里展开规划结构与章节细纲。\n\n"
    "用章节悬念节奏法压住推进，但不要输出推理过程：\n"
    "- 3-5章构成一个悬念单元，每个单元包含一次小高潮或强兑现\n"
    "- 使用认知过山车模式：连续2章紧张后安排1章缓冲或关系/奖励兑现\n"
    "- 伏笔三步法：埋设 → 强化 → 回收，标注关键伏笔在章节中的位置\n"
    "- 设计认知颠覆曲线，避免连续章节只有同一种信息增量\n\n"
    "每个规划块用二级标题（## ）标注该阶段、卷或幕的名称与主题，必要时可在标题下补一行引用（> ）说明当前局面。\n"
    "需要拆到章节时，再在对应规划块下使用三级标题（### ）列出章节。\n"
    "不要输出顶层一级标题（# ）；卷级字段只能用项目符号、加粗字段或引用行表达，不要使用三级标题（### ）。\n"
    "只有真实章节可以使用三级标题，且必须写成「### 第 N 章：章名」。\n"
    "章节细纲是机器解析契约：禁止用 Markdown 表格、范围章或列表摘要代替真实章节块；如果规划里出现「第9-11章」这种范围，必须拆成第9章、第10章、第11章三个独立三级标题。\n"
    "不要求固定写成三幕、几卷或多少章，应由故事实际推进需要决定结构层级。\n\n"
    "每章必须包含：\n"
    "- **章节标题**\n"
    "- **核心事件**（2-3 句话概括）\n"
    "- **情绪走向**（如「平静 → 疑惑 → 震惊 → 愤怒」，或「极致爽感」、「沉沦堕落」）\n"
    "- **章末钩子**（可以是悬念、反转、新压力、关系变化或阶段性兑现）\n\n"
    "节奏规则：\n"
    "- 同一规划块内的章节情绪应有起伏，但在高潮或欲望满足环节允许连续的情绪宣泄\n"
    "- 允许出现纯粹服务于欲望满足、打脸装逼、后宫日常的章节，无需强求传统局面推进\n"
    "- 不必每章硬凹爆点，关键是明确下一章的兑现期待\n"
    "- 该收束时安排伏笔回收和主线收口，但不要机械地按篇幅预设倒推结构\n"
    "- 每章都要回答：下一章读者到底在等什么兑现\n"
    "- 兑现可以是拿到资源、完成打脸、扳回压制、彻底推倒、精神与肉体双重控制或阶层跃升\n"
    "- 悬念必须明确勾着特定的多巴胺反馈、征服欲或生理/情感期待"
    "{hook_framework}"
)

_VOLUME_CHAPTERS_SYSTEM_TEMPLATE = (
    "你是一位起点白金作家，正在为自己的当前卷拆章节细纲，控制章节推进、情绪起伏和章末钩子。\n\n"
    f"{MALE_COMMERCIAL_ENGINE}"
    "{planning_budget_hint}\n\n"
    "为指定的卷设计章节。每章用三级标题（### ），格式如下：\n\n"
    "### 第 N 章：章名\n"
    "- **核心事件**：一句话概括\n"
    "- **情绪走向**：如「平静 → 震惊 → 愤怒」\n"
    "- **章末钩子**：驱动读者继续阅读的悬念或反转\n\n"
    "输出契约（必须严格遵守，否则结果无法进入章节树）：\n"
    "- 只能输出连续的真实章节块，不要输出卷标题、卷级分析、节奏设计、主要节奏、章末压力设计或总结段\n"
    "- 禁止输出 Markdown 表格，禁止用项目符号列表批量概括多个章节\n"
    "- 禁止输出「第9-11章」这类范围章；必须展开成「### 第 9 章：...」「### 第 10 章：...」「### 第 11 章：...」\n"
    "- 每个章节块必须同时包含「核心事件」「情绪走向」「章末钩子」三个加粗字段\n\n"
    "落笔规则：\n"
    "- 不要输出顶层一级标题（# ）\n"
    "- 三级标题只用于真实章节，必须写成「### 第 N 章：章名」\n"
    "- 只为当前卷输出章节详纲，不要顺手拆后续卷章节\n"
    "- 章节之间情绪有起伏，不要连续同一情绪\n"
    "- 每章末必须有钩子\n"
    "- 每章末推动点要能让人立刻知道下一章最想看的兑现是什么\n"
    "- 参考已有的前几卷章节，保持情节连贯\n"
    "- 直接输出章节列表，不要输出卷标题，不要添加解释"
    "{hook_framework}"
)


def build_outline_detail_system_prompt(
    style_prompt: str | None = None,
    plot_prompt: str | None = None,
    generation_profile: GenerationProfile | None = None,
    length_preset: LengthPresetKey = "long",
    regenerating: bool = False,
) -> str:
    hook_framework = get_hook_framework(generation_profile)
    instruction = append_soft_length_hint(
        _OUTLINE_DETAIL_INSTRUCTION_TEMPLATE.format(hook_framework=hook_framework),
        length_preset,
    )
    instruction += build_volume_planning_budget_hint(length_preset)
    parts: list[str] = []
    append_profile_blocks(
        parts,
        style_prompt=style_prompt,
        plot_prompt=plot_prompt,
        plot_usage="只吸收压力系统、推进节奏、角色功能位和兑现逻辑，不得照搬样本角色、设定、事件。",
        generation_profile=generation_profile,
    )
    parts.append(
        "你是一位起点白金作家，正在为自己的新书搭设定、排结构、拆章法，现在要完成「分卷与章节细纲」。\n"
        f"{MALE_COMMERCIAL_ENGINE}"
        f"{instruction}\n\n"
        "落笔规则：\n"
        "- 使用 Markdown 格式，标题层级清晰\n"
        "- 不要输出顶层一级标题（# ）\n"
        "- 卷级字段不要使用三级标题（### ），只有真实章节可使用「### 第 N 章：章名」\n"
        "- 具体且有用，避免空泛概括\n"
        "- 直接输出内容，不要添加任何解释性前言或总结"
    )
    if regenerating:
        parts.append(REGENERATION_GUIDANCE)
    return "\n".join(parts)


def build_outline_detail_user_message(
    context: dict[str, str],
    previous_output: str | None = None,
    user_feedback: str | None = None,
) -> str:
    return build_section_user_message(
        "outline_detail",
        context,
        previous_output=previous_output,
        user_feedback=user_feedback,
    )


def build_volume_chapters_system_prompt(
    length_preset: LengthPresetKey = "long",
    style_prompt: str | None = None,
    plot_prompt: str | None = None,
    generation_profile: GenerationProfile | None = None,
    regenerating: bool = False,
) -> str:
    parts: list[str] = []
    append_profile_blocks(
        parts,
        style_prompt=style_prompt,
        plot_prompt=plot_prompt,
        plot_usage="用它拆章节闭环、章末推动点和关系/资源状态变化，不得照搬样本桥段。",
        generation_profile=generation_profile,
    )
    hook_framework = get_hook_framework(generation_profile)
    parts.append(
        _VOLUME_CHAPTERS_SYSTEM_TEMPLATE.format(
            planning_budget_hint=build_volume_planning_budget_hint(length_preset).strip(),
            hook_framework=hook_framework,
        )
    )
    if regenerating:
        parts.append(REGENERATION_GUIDANCE)
    return "\n".join(parts)


def build_volume_chapters_user_message(
    outline_master: str,
    volume_title: str,
    volume_meta: str,
    preceding_chapters_summary: str,
    volume_body_markdown: str = "",
    previous_output: str | None = None,
    user_feedback: str | None = None,
) -> str:
    parts: list[str] = []
    if outline_master.strip():
        parts.append(f"## 总纲\n\n{outline_master}")
    current_volume_parts = [f"**{volume_title}**"]
    if volume_meta.strip():
        current_volume_parts.append(volume_meta.strip())
    if volume_body_markdown.strip():
        current_volume_parts.append(f"### 当前卷原始规划\n\n{volume_body_markdown.strip()}")
    parts.append("## 当前卷\n\n" + "\n\n".join(current_volume_parts))
    if preceding_chapters_summary.strip():
        parts.append(
            f"## 前几卷已有章节（参考，保持连贯）\n\n{preceding_chapters_summary}"
        )
    append_regeneration_context(parts, previous_output, user_feedback)
    parts.append("请为当前卷设计章节细纲。只输出标准章节块，不要输出表格、范围章或卷级说明：")
    return "\n\n---\n\n".join(parts)
