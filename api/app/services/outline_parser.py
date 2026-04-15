"""Markdown outline_detail 解析器。

将规范化的 Markdown 文本解析为结构化的卷/章字典，
并提供将生成的章节插入到指定卷位置的工具函数。
"""

from __future__ import annotations

import re
from typing import TypedDict


class ParsedChapter(TypedDict):
    title: str
    core_event: str
    emotion_arc: str
    chapter_hook: str
    raw_markdown: str


class ParsedVolume(TypedDict):
    title: str
    meta: str
    chapters: list[ParsedChapter]


class ParsedOutline(TypedDict):
    volumes: list[ParsedVolume]
    parse_errors: list[str]


def _extract_field(text: str, field_name: str) -> str:
    m = re.search(rf"\*\*{field_name}\*\*[：:]\s*(.+)", text)
    return m.group(1).strip() if m else ""


def parse_outline(markdown: str) -> ParsedOutline:
    """解析 outline_detail Markdown 为结构化卷/章数据。"""
    if not markdown.strip():
        return {"volumes": [], "parse_errors": []}

    volume_splits = re.split(r"^(?=## )", markdown, flags=re.MULTILINE)
    volume_blocks = [b for b in volume_splits if b.strip()]

    volumes: list[ParsedVolume] = []
    parse_errors: list[str] = []

    for block in volume_blocks:
        title_match = re.match(r"^## (.+)$", block, re.MULTILINE)
        if not title_match:
            if block.strip():
                parse_errors.append(f"无法识别的内容块: {block[:50]}...")
            continue

        title = title_match.group(1).strip()
        meta_match = re.search(r"^>\s*(.+)$", block, re.MULTILINE)
        meta = meta_match.group(1).strip() if meta_match else ""

        chapter_splits = re.split(r"^(?=### )", block, flags=re.MULTILINE)
        chapters: list[ParsedChapter] = []

        for ch_block in chapter_splits:
            ch_title_match = re.match(r"^### (.+)$", ch_block, re.MULTILINE)
            if not ch_title_match:
                continue
            ch_title = ch_title_match.group(1).strip()
            chapters.append({
                "title": ch_title,
                "core_event": _extract_field(ch_block, "核心事件"),
                "emotion_arc": _extract_field(ch_block, "情绪走向"),
                "chapter_hook": _extract_field(ch_block, "章末钩子"),
                "raw_markdown": ch_block.strip(),
            })

        volumes.append({"title": title, "meta": meta, "chapters": chapters})

    if not volumes:
        parse_errors.append("无法识别分卷结构（需要 ## 标题）")

    return {"volumes": volumes, "parse_errors": parse_errors}


def insert_chapters_into_volume(
    outline_detail: str,
    volume_index: int,
    chapters_markdown: str,
) -> str:
    """将生成的章节 Markdown 插入到 outline_detail 的指定卷位置。"""
    volume_starts = [m.start() for m in re.finditer(r"^## ", outline_detail, re.MULTILINE)]

    if volume_index < 0 or volume_index >= len(volume_starts):
        return outline_detail + "\n\n" + chapters_markdown

    vol_start = volume_starts[volume_index]

    if volume_index + 1 < len(volume_starts):
        vol_end = volume_starts[volume_index + 1]
    else:
        vol_end = len(outline_detail)

    vol_content = outline_detail[vol_start:vol_end].rstrip()
    new_vol_content = vol_content + "\n\n" + chapters_markdown.strip() + "\n\n"

    return outline_detail[:vol_start] + new_vol_content + outline_detail[vol_end:]
