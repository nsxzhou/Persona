"""Shared metadata for the story bible sections (blueprint + runtime layers).

Used by context_assembly, editor_prompts, and any other module that needs
a canonical list of bible field keys and their human-readable labels.
"""

from __future__ import annotations

BLUEPRINT_SECTION_ORDER: list[tuple[str, str]] = [
    ("灵感概述", "inspiration"),
    ("世界观设定", "world_building"),
    ("角色设定", "characters"),
    ("总纲", "outline_master"),
    ("分卷与章节细纲", "outline_detail"),
]
"""(label, field_key) pairs for author-controlled blueprint fields."""

RUNTIME_SECTION_ORDER: list[tuple[str, str]] = [
    ("运行时状态", "runtime_state"),
    ("伏笔与线索追踪", "runtime_threads"),
]
"""(label, field_key) pairs for AI-updated runtime fields."""

BIBLE_SECTION_ORDER: list[tuple[str, str]] = (
    BLUEPRINT_SECTION_ORDER + RUNTIME_SECTION_ORDER
)
"""All sections in canonical display order (blueprint first, then runtime)."""

BIBLE_FIELD_KEYS: list[str] = [key for _, key in BIBLE_SECTION_ORDER]
BLUEPRINT_FIELD_KEYS: list[str] = [key for _, key in BLUEPRINT_SECTION_ORDER]
RUNTIME_FIELD_KEYS: list[str] = [key for _, key in RUNTIME_SECTION_ORDER]

BIBLE_FIELD_LABELS: dict[str, str] = {
    key: label for label, key in BIBLE_SECTION_ORDER
}
