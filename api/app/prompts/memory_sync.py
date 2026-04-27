from __future__ import annotations

import re

from app.prompts.common import REGENERATION_GUIDANCE, append_regeneration_context

_BIBLE_UPDATE_SYSTEM = (
    "你是一位长期连载中的成熟作者，正在维护自己的角色状态、设定备忘与伏笔追踪。\n"
    "当前任务是：根据刚写出的最新正文，维护和更新项目的【长期 persistent 事件列表】（即运行时状态）、角色动态状态和伏笔线索。\n\n"
    "【核心原则】\n"
    "1. 严禁像流水账一样记录每章剧情，只能保留对后续章节有长远影响的剧情变化、人物状态、未解决伏笔。\n"
    "2. 一次性动作、战斗过程、心理描写、气氛渲染等非持久性信息，绝对不要记录。\n"
    "3. 优先判断是否无需更新：如果本段正文没有实质性改变，你可以完全照抄当前内容，不要强行编造。\n"
    "4. 输出两个区块的完整最终版本（可直接替换旧文档）以及角色动态状态。你输出的内容将直接覆盖数据库。即使只有一处小改动，你也必须把未改变的部分完整写出来。\n"
    "5. 严禁使用“保留原有/同上/沿用旧内容/并追加以下/其余不变”等指代或占位语。\n"
    "6. 严禁使用“沿用旧内容”这类偷懒表述。\n"
    "7. 新增事件、角色、伏笔必须与旧信息合并后完整输出，不能只输出增量。\n"
    "8. 只记录会持续影响后续选择的关系变化、利益交换，或金手指/系统的升级进度。\n"
    "9. 准确记录关系进阶的里程碑，包括情感投射的加深、身体关系的突破（如一垒、二垒、本垒打等）、控制深度的增加或堕落阶段的演进。\n"
    "10. 必须记录能提供“纯粹爽感”、“权力具象化”或“打破禁忌”成果的关键进展。\n\n"
    "【输出格式】\n"
    "- 必须包含「## 角色动态状态」、「## 运行时状态」和「## 伏笔与线索追踪」三个二级标题\n"
    "- 直接输出内容，不要添加解释"
)

_CHAPTER_SUMMARY_SYSTEM = (
    "你是一个专业的小说章节摘要助手。\n"
    "请根据传入的章节正文，生成约 300 字的精简摘要。\n"
    "摘要只需保留：「对后续章节有影响的剧情变化、人物状态、未解决伏笔」。\n"
    "直接输出摘要文本，不要包含任何标题、解释或多余的客套话。"
)


def parse_bible_update_response(raw: str) -> tuple[str, str, str]:
    characters_status = ""
    runtime_state = ""
    runtime_threads = ""

    parts = re.split(r"(?m)^(##\s+.*)$", raw)
    current_heading = None

    for part in (part.strip() for part in parts):
        if not part:
            continue
        if part.startswith("##"):
            current_heading = part
        elif current_heading:
            if "角色动态状态" in current_heading:
                characters_status = part
            elif "运行时状态" in current_heading:
                runtime_state = part
            elif "伏笔与线索追踪" in current_heading:
                runtime_threads = part
        else:
            characters_status = part

    return characters_status, runtime_state, runtime_threads


def build_bible_update_system_prompt(regenerating: bool = False) -> str:
    if regenerating:
        return _BIBLE_UPDATE_SYSTEM + REGENERATION_GUIDANCE
    return _BIBLE_UPDATE_SYSTEM


def build_chapter_summary_system_prompt() -> str:
    return _CHAPTER_SUMMARY_SYSTEM


def build_chapter_summary_user_message(content: str) -> str:
    return f"## 章节正文\n\n{content}"


def build_bible_update_user_message(
    *,
    current_characters_status: str = "",
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

    if current_characters_status.strip():
        parts.append(f"## 当前角色动态状态\n\n{current_characters_status}")
    else:
        parts.append("## 当前角色动态状态\n\n（空，尚未建立）")

    if current_runtime_state.strip():
        parts.append(f"## 当前运行时状态\n\n{current_runtime_state}")
    else:
        parts.append("## 当前运行时状态\n\n（空，尚未建立）")

    if current_runtime_threads.strip():
        parts.append(f"## 当前伏笔与线索追踪\n\n{current_runtime_threads}")
    else:
        parts.append("## 当前伏笔与线索追踪\n\n（空，尚未建立）")

    parts.append(f"{scope_label}\n\n{content_to_check}")
    append_regeneration_context(parts, previous_output, user_feedback)
    return "\n\n---\n\n".join(parts)


def build_story_summary_system_prompt() -> str:
    return (
        "你是一位专业的故事内容整理师，负责维护小说的全局进展摘要。\n"
        "请根据既有全局摘要与最新章节正文，更新全局故事摘要。\n"
        "必须保留重要历史信息，只删除已失效或被推翻的信息。\n"
        "输出 Markdown，并包含「## 全局故事摘要 (GLOBAL_SUMMARY_UPDATED)」标题。"
    )


def build_story_summary_user_message(
    *,
    current_story_summary: str,
    prose_markdown: str,
) -> str:
    return (
        f"## 既有全局摘要\n\n{current_story_summary}\n\n"
        f"## 最新章节正文\n\n{prose_markdown}"
    )
