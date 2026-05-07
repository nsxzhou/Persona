from __future__ import annotations

from app.core.bible_fields import BIBLE_FIELD_KEYS, BIBLE_FIELD_LABELS
from app.prompts.common import append_regeneration_context


def build_section_user_message(
    section: str,
    context: dict[str, str],
    previous_output: str | None = None,
    user_feedback: str | None = None,
) -> str:
    project_name = (context.get("project_name") or "").strip()
    context_parts: list[str] = []
    for key in BIBLE_FIELD_KEYS:
        if key == section:
            continue
        text = context.get(key, "").strip()
        if text:
            label = BIBLE_FIELD_LABELS[key]
            context_parts.append(f"## {label}\n\n{text}")

    parts: list[str] = []
    if project_name:
        parts.append(
            "## 项目小说名（硬约束）\n\n"
            f"{project_name}\n\n"
            "若输出书名、一级标题或总纲标题，必须逐字使用上面的项目小说名；"
            "可以按排版需要加《》书名号，但不得改字、换名或沿用样本/旧稿书名。"
        )
    if context_parts:
        parts.append(
            "以下是当前已有的创作设定：\n\n" + "\n\n---\n\n".join(context_parts)
        )
    else:
        parts.append("（没有其他设定，直接按当前创意开局）")
    append_regeneration_context(parts, previous_output, user_feedback)
    return "\n\n---\n\n".join(parts)
