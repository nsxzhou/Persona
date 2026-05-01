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
    body_markdown: str
    chapters: list[ParsedChapter]


class ParsedOutline(TypedDict):
    volumes: list[ParsedVolume]
    parse_errors: list[str]


def _extract_field(text: str, field_name: str) -> str:
    m = re.search(rf"\*\*{field_name}\*\*[：:]\s*(.+)", text)
    return m.group(1).strip() if m else ""


def _extract_first_field(text: str, field_names: tuple[str, ...]) -> str:
    for field_name in field_names:
        value = _extract_field(text, field_name)
        if value:
            return value
    return ""


VOLUME_HEADING_RE = re.compile(r"^## (?!#)(.+)$", re.MULTILINE)
CHAPTER_HEADING_RE = re.compile(
    r"^###\s+第\s*(?:\d+|[一二三四五六七八九十百千万零〇两]+)\s*章.*$",
    re.MULTILINE,
)
CHAPTER_SPLIT_RE = re.compile(
    r"(?=^###\s+第\s*(?:\d+|[一二三四五六七八九十百千万零〇两]+)\s*章.*$)",
    re.MULTILINE,
)


def _has_chapter_heading(text: str) -> bool:
    return CHAPTER_HEADING_RE.search(text) is not None


def _is_ignorable_section_title(title: str) -> bool:
    return "闭环验证" in re.sub(r"\s+", "", title)


def _parse_chapter(ch_block: str) -> ParsedChapter | None:
    ch_title_match = CHAPTER_HEADING_RE.search(ch_block)
    if not ch_title_match:
        return None
    ch_title = ch_title_match.group(0).replace("###", "", 1).strip()
    return {
        "title": ch_title,
        "core_event": _extract_field(ch_block, "核心事件"),
        "emotion_arc": _extract_field(ch_block, "情绪走向"),
        "chapter_hook": _extract_first_field(
            ch_block,
            ("章末钩子", "章节末推动点"),
        ),
        "raw_markdown": ch_block.strip(),
    }


def _parse_volume_block(block: str, title: str) -> ParsedVolume:
    meta_match = re.search(r"^>\s*(.+)$", block, re.MULTILINE)
    meta = meta_match.group(1).strip() if meta_match else ""

    first_chapter_match = CHAPTER_HEADING_RE.search(block)
    if first_chapter_match:
        body_markdown = block[: first_chapter_match.start()].strip()
        chapter_markdown = block[first_chapter_match.start():]
    else:
        body_markdown = block.strip()
        chapter_markdown = ""

    chapters: list[ParsedChapter] = []
    for ch_block in CHAPTER_SPLIT_RE.split(chapter_markdown):
        chapter = _parse_chapter(ch_block)
        if chapter is not None:
            chapters.append(chapter)

    return {
        "title": title,
        "meta": meta,
        "body_markdown": body_markdown,
        "chapters": chapters,
    }


def parse_outline(markdown: str) -> ParsedOutline:
    """解析 outline_detail Markdown 为结构化卷/章数据。"""
    if not markdown.strip():
        return {"volumes": [], "parse_errors": []}

    volume_matches = list(VOLUME_HEADING_RE.finditer(markdown))
    has_chapter_headings = _has_chapter_heading(markdown)

    if not volume_matches and not has_chapter_headings:
        return {"volumes": [], "parse_errors": [markdown.strip()]}

    if not volume_matches and has_chapter_headings:
        return {
            "volumes": [_parse_volume_block(markdown, "")],
            "parse_errors": [],
        }

    volumes: list[ParsedVolume] = []

    for index, match in enumerate(volume_matches):
        block_end = (
            volume_matches[index + 1].start()
            if index + 1 < len(volume_matches)
            else len(markdown)
        )
        title = match.group(1).strip()
        body = markdown[match.end():block_end]

        if _is_ignorable_section_title(title) and not _has_chapter_heading(body):
            continue

        volumes.append(_parse_volume_block(body, title))

    if not volumes:
        return {"volumes": [], "parse_errors": [markdown.strip()]}

    return {"volumes": volumes, "parse_errors": []}


def insert_chapters_into_volume(
    outline_detail: str,
    volume_index: int,
    chapters_markdown: str,
) -> str:
    """将生成的章节 Markdown 插入到 outline_detail 的指定卷位置。"""
    volume_starts = [m.start() for m in VOLUME_HEADING_RE.finditer(outline_detail)]

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
