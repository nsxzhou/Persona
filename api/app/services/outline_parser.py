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
CHAPTER_REF_RE = re.compile(
    r"第\s*(\d+|[一二三四五六七八九十百千万零〇两]+)\s*"
    r"(?:[-~－–—至到]\s*(\d+|[一二三四五六七八九十百千万零〇两]+))?\s*章"
)


class _H3Section(TypedDict):
    title: str
    start: int
    end: int
    body: str


class _ChapterReference(TypedDict):
    numbers: list[int]
    match_end: int


class _FallbackChapterDraft(ParsedChapter):
    chapter_number: int


def _has_chapter_heading(text: str) -> bool:
    return CHAPTER_HEADING_RE.search(text) is not None


def has_standard_chapter_headings(text: str) -> bool:
    return _has_chapter_heading(text)


def _is_ignorable_section_title(title: str) -> bool:
    normalized = re.sub(r"\s+", "", title)
    return any(keyword in normalized for keyword in ("闭环验证", "全篇爽点密度表"))


def _parse_chinese_number(value: str) -> int | None:
    digits = {
        "零": 0,
        "〇": 0,
        "一": 1,
        "二": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
    }
    units = {"十": 10, "百": 100, "千": 1000, "万": 10000}
    total = 0
    section = 0
    number = 0
    consumed = False

    for char in value:
        if char in digits:
            number = digits[char]
            consumed = True
            continue
        unit = units.get(char)
        if unit is None:
            return None
        consumed = True
        if unit == 10000:
            total += (section + number or 1) * unit
            section = 0
            number = 0
        else:
            section += (number or 1) * unit
            number = 0

    result = total + section + number
    return result if consumed and result > 0 else None


def _parse_chapter_number(value: str) -> int | None:
    if value.isdigit():
        return int(value)
    return _parse_chinese_number(value)


def _expand_chapter_numbers(start: int, end: int | None) -> list[int]:
    if start <= 0:
        return []
    if end is None or end < start or end - start > 100:
        return [start]
    return list(range(start, end + 1))


def _parse_chapter_reference(text: str) -> _ChapterReference | None:
    match = CHAPTER_REF_RE.search(text)
    if not match:
        return None
    start = _parse_chapter_number(match.group(1))
    if start is None:
        return None
    end = _parse_chapter_number(match.group(2)) if match.group(2) else None
    return {
        "numbers": _expand_chapter_numbers(start, end),
        "match_end": match.end(),
    }


def _clean_inline_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\*\*", "", re.sub(r"<br\s*/?>", " ", value))).strip()


def _extract_h3_sections(block: str) -> list[_H3Section]:
    matches = list(re.finditer(r"^###\s+(.+)$", block, re.MULTILINE))
    sections: list[_H3Section] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(block)
        sections.append(
            {
                "title": match.group(1).strip(),
                "start": match.start(),
                "end": end,
                "body": block[match.end():end].strip(),
            }
        )
    return sections


def _is_fallback_chapter_section(title: str) -> bool:
    normalized = re.sub(r"\s+", "", title)
    return "节奏设计" in normalized or "主要节奏" in normalized


def _is_fallback_hook_section(title: str) -> bool:
    return "章末" in re.sub(r"\s+", "", title)


def _has_fallback_chapter_sections(text: str) -> bool:
    return any(_is_fallback_chapter_section(section["title"]) for section in _extract_h3_sections(text))


def _split_table_row(line: str) -> list[str]:
    return [_clean_inline_text(cell) for cell in line.strip().strip("|").split("|")]


def _is_table_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", re.sub(r"\s+", "", cell)) for cell in cells)


def _build_fallback_chapter(
    chapter_number: int,
    summary: str,
    hook: str,
) -> _FallbackChapterDraft:
    normalized_summary = _clean_inline_text(summary)
    normalized_hook = _clean_inline_text(hook)
    title = f"第{chapter_number}章：{normalized_summary}" if normalized_summary else f"第{chapter_number}章"
    raw_parts = [f"### {title}"]
    if normalized_summary:
        raw_parts.append(f"- **核心事件**：{normalized_summary}")
    if normalized_hook:
        raw_parts.append(f"- **章末钩子**：{normalized_hook}")
    return {
        "chapter_number": chapter_number,
        "title": title,
        "core_event": normalized_summary,
        "emotion_arc": "",
        "chapter_hook": normalized_hook,
        "raw_markdown": "\n".join(raw_parts),
    }


def _extract_chapter_hooks(block: str) -> dict[int, str]:
    hooks: dict[int, str] = {}
    for section in _extract_h3_sections(block):
        if not _is_fallback_hook_section(section["title"]):
            continue
        for line in section["body"].splitlines():
            item = re.match(r"^\s*[-*+]\s+(.+)$", line)
            if not item:
                continue
            text = item.group(1)
            ref = _parse_chapter_reference(text)
            if ref is None:
                continue
            hook = _clean_inline_text(
                re.sub(r"^\s*(?:结尾)?\s*[：:，,、\-—]\s*", "", text[ref["match_end"] :])
            )
            if not hook:
                continue
            for chapter_number in ref["numbers"]:
                hooks[chapter_number] = hook
    return hooks


def _parse_fallback_table_chapters(
    section_body: str,
    hooks: dict[int, str],
) -> list[_FallbackChapterDraft]:
    rows = [
        _split_table_row(line)
        for line in section_body.splitlines()
        if line.strip().startswith("|") and "|" in line
    ]
    rows = [row for row in rows if any(row)]
    header_index = next(
        (index for index, row in enumerate(rows) if any("章号" in cell for cell in row)),
        -1,
    )
    if header_index == -1:
        return []

    header = rows[header_index]
    chapter_column = next((index for index, cell in enumerate(header) if "章号" in cell), 0)
    content_column = next(
        (
            index
            for index, cell in enumerate(header)
            if index != chapter_column and re.search(r"内容|事件|剧情", cell)
        ),
        -1,
    )
    hook_column = next(
        (index for index, cell in enumerate(header) if re.search(r"追读|驱动|钩子|悬念", cell)),
        -1,
    )
    chapters: list[_FallbackChapterDraft] = []

    for row in rows[header_index + 1 :]:
        if _is_table_separator_row(row):
            continue
        chapter_cell = row[chapter_column] if chapter_column < len(row) else ""
        if not _parse_chapter_reference(chapter_cell):
            chapter_cell = next((cell for cell in row if _parse_chapter_reference(cell)), "")
        ref = _parse_chapter_reference(chapter_cell)
        if ref is None:
            continue
        summary = (
            row[content_column]
            if content_column >= 0 and content_column < len(row)
            else " ".join(cell for index, cell in enumerate(row) if index not in (chapter_column, hook_column))
        )
        row_hook = row[hook_column] if hook_column >= 0 and hook_column < len(row) else ""
        for chapter_number in ref["numbers"]:
            chapters.append(_build_fallback_chapter(chapter_number, summary, hooks.get(chapter_number, row_hook)))

    return chapters


def _parse_fallback_list_chapters(
    section_body: str,
    hooks: dict[int, str],
) -> list[_FallbackChapterDraft]:
    chapters: list[_FallbackChapterDraft] = []
    for line in section_body.splitlines():
        item = re.match(r"^\s*[-*+]\s+(.+)$", line)
        if not item:
            continue
        text = item.group(1)
        ref = _parse_chapter_reference(text)
        if ref is None:
            continue
        summary = _clean_inline_text(re.sub(r"^\s*[：:，,、\-—]\s*", "", text[ref["match_end"] :]))
        if not summary:
            continue
        for chapter_number in ref["numbers"]:
            chapters.append(_build_fallback_chapter(chapter_number, summary, hooks.get(chapter_number, "")))
    return chapters


def _parse_fallback_chapters(block: str) -> list[ParsedChapter]:
    hooks = _extract_chapter_hooks(block)
    chapters: list[ParsedChapter] = []
    seen_chapter_numbers: set[int] = set()

    for section in _extract_h3_sections(block):
        if not _is_fallback_chapter_section(section["title"]):
            continue
        drafts = [
            *_parse_fallback_table_chapters(section["body"], hooks),
            *_parse_fallback_list_chapters(section["body"], hooks),
        ]
        for draft in drafts:
            chapter_number = draft["chapter_number"]
            if chapter_number in seen_chapter_numbers:
                continue
            seen_chapter_numbers.add(chapter_number)
            chapters.append(
                {
                    "title": draft["title"],
                    "core_event": draft["core_event"],
                    "emotion_arc": draft["emotion_arc"],
                    "chapter_hook": draft["chapter_hook"],
                    "raw_markdown": draft["raw_markdown"],
                }
            )

    return chapters


def _remove_fallback_chapter_sections(block: str) -> str:
    sections = [
        section
        for section in _extract_h3_sections(block)
        if _is_fallback_chapter_section(section["title"]) or _is_fallback_hook_section(section["title"])
    ]
    if not sections:
        return block.strip()

    result = ""
    cursor = 0
    for section in sections:
        result += block[cursor:section["start"]]
        cursor = section["end"]
    result += block[cursor:]
    return re.sub(r"\n{3,}", "\n\n", result).strip()


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

    fallback_chapters = _parse_fallback_chapters(block) if not chapters else []
    final_body_markdown = _remove_fallback_chapter_sections(block) if fallback_chapters else body_markdown

    return {
        "title": title,
        "meta": meta,
        "body_markdown": final_body_markdown,
        "chapters": chapters or fallback_chapters,
    }


def parse_outline(markdown: str) -> ParsedOutline:
    """解析 outline_detail Markdown 为结构化卷/章数据。"""
    if not markdown.strip():
        return {"volumes": [], "parse_errors": []}

    volume_matches = list(VOLUME_HEADING_RE.finditer(markdown))
    has_chapter_headings = _has_chapter_heading(markdown)
    has_fallback_headings = _has_fallback_chapter_sections(markdown)

    if not volume_matches and not has_chapter_headings and not has_fallback_headings:
        return {"volumes": [], "parse_errors": [markdown.strip()]}

    if not volume_matches and (has_chapter_headings or has_fallback_headings):
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

        if _is_ignorable_section_title(title) and not _has_chapter_heading(body) and not _has_fallback_chapter_sections(body):
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
