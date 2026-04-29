from __future__ import annotations


def build_active_characters_system_prompt() -> str:
    return (
        "请从章节上下文和近期片段里提取当前场景中「正在出场」或「即将出场」、会影响当前推进的角色姓名。\n"
        "只认角色名，不要把势力名、地点名、称号或关系标签当成角色。\n"
        "只需返回包含角色姓名的 JSON 数组（字符串列表），例如：[\"张三\", \"李四\"]。\n"
        "如果没有任何角色出场，请返回空数组 []。\n"
        "不要包含任何其他文字或解释。"
    )


def build_active_characters_user_message(
    text_before_cursor: str,
    current_chapter_context: str,
) -> str:
    parts = []
    if current_chapter_context.strip():
        parts.append(f"## 当前章节上下文\n\n{current_chapter_context}")
    if text_before_cursor.strip():
        parts.append(f"## 近期正文片段\n\n{text_before_cursor[-2000:]}")
    return "\n\n---\n\n".join(parts)
