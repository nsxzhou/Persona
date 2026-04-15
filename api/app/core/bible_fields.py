"""Shared metadata for the six story bible sections.

Used by context_assembly, editor_prompts, and any other module that needs
a canonical list of bible field keys and their human-readable labels.
"""

from __future__ import annotations

BIBLE_SECTION_ORDER: list[tuple[str, str]] = [
    ("灵感概述", "inspiration"),
    ("世界观设定", "world_building"),
    ("角色设定", "characters"),
    ("总纲", "outline_master"),
    ("分卷与章节细纲", "outline_detail"),
    ("故事圣经补充", "story_bible"),
]
"""(label, field_key) pairs in canonical display order."""

BIBLE_FIELD_KEYS: list[str] = [key for _, key in BIBLE_SECTION_ORDER]

BIBLE_FIELD_LABELS: dict[str, str] = {
    key: label for label, key in BIBLE_SECTION_ORDER
}
