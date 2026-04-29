from __future__ import annotations

from app.core.bible_fields import BIBLE_FIELD_KEYS, BIBLE_FIELD_LABELS
from app.prompts.common import append_regeneration_context


def build_section_user_message(
    section: str,
    context: dict[str, str],
    previous_output: str | None = None,
    user_feedback: str | None = None,
) -> str:
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
        parts.append("（没有其他设定，直接按当前创意开局）")
    append_regeneration_context(parts, previous_output, user_feedback)
    return "\n\n---\n\n".join(parts)
