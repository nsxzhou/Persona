from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Literal

import yaml


ChapterRewritePlanOperation = Literal["insert_after", "replace"]

_FRONT_MATTER_RE = re.compile(r"\A---[ \t]*\n(?P<yaml>.*?)(?:\n---[ \t]*\n?)(?P<body>.*)\Z", re.DOTALL)
_PARAGRAPH_BREAK_RE = re.compile(r"\n[ \t]*\n")


@dataclass(frozen=True)
class ChapterRewriteParagraph:
    id: str
    text: str
    start: int
    end: int
    index: int


@dataclass(frozen=True)
class ChapterRewriteEdit:
    operation: ChapterRewritePlanOperation
    paragraph_id: str
    new_text: str


@dataclass(frozen=True)
class ChapterRewritePlan:
    edits: list[ChapterRewriteEdit]


def build_numbered_chapter_rewrite_source(original: str) -> str:
    paragraphs = split_chapter_rewrite_paragraphs(original)
    if not paragraphs:
        raise ValueError("当前章节正文为空，无法改写")
    return "\n\n".join(f"[{paragraph.id}]\n{paragraph.text}" for paragraph in paragraphs)


def split_chapter_rewrite_paragraphs(original: str) -> list[ChapterRewriteParagraph]:
    paragraphs: list[ChapterRewriteParagraph] = []
    paragraph_index = 1
    cursor = 0
    for match in _PARAGRAPH_BREAK_RE.finditer(original):
        cursor = _append_rewrite_paragraph(
            paragraphs,
            original,
            cursor,
            match.start(),
            paragraph_index,
        )
        if len(paragraphs) == paragraph_index:
            paragraph_index += 1
        cursor = match.end()
    _append_rewrite_paragraph(
        paragraphs,
        original,
        cursor,
        len(original),
        paragraph_index,
    )
    return paragraphs


def parse_chapter_rewrite_plan(front_matter_markdown: str) -> ChapterRewritePlan:
    stripped = front_matter_markdown.strip()
    if not stripped:
        raise ValueError("章节改写计划输出为空")

    match = _FRONT_MATTER_RE.fullmatch(stripped)
    if match is None:
        raise ValueError("章节改写计划必须只包含 YAML front matter")
    if match.group("body").strip():
        raise ValueError("章节改写计划不得包含 YAML front matter 之外的正文")

    try:
        payload = yaml.safe_load(match.group("yaml"))
    except yaml.YAMLError as exc:
        raise ValueError(f"章节改写计划 YAML 解析失败: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("章节改写计划 YAML 顶层必须是对象")
    raw_edits = payload.get("edits")
    if not isinstance(raw_edits, list) or not raw_edits:
        raise ValueError("章节改写计划 edits 必须是非空列表")

    edits: list[ChapterRewriteEdit] = []
    seen_paragraph_ids: set[str] = set()
    for index, raw_edit in enumerate(raw_edits, start=1):
        if not isinstance(raw_edit, dict):
            raise ValueError(f"章节改写计划 Edit {index} 必须是对象")

        operation = _required_string(raw_edit, "operation", index)
        if operation not in {"insert_after", "replace"}:
            raise ValueError(f"章节改写计划 Edit {index} 操作不支持: {operation}")

        paragraph_id = _required_string(raw_edit, "paragraph_id", index)
        if not re.fullmatch(r"P\d{3,}", paragraph_id):
            raise ValueError(f"章节改写计划 Edit {index} paragraph_id 格式不正确")
        if paragraph_id in seen_paragraph_ids:
            raise ValueError(f"章节改写计划重复使用 paragraph_id: {paragraph_id}")
        seen_paragraph_ids.add(paragraph_id)

        new_text = _required_string(raw_edit, "new_text", index)
        edits.append(
            ChapterRewriteEdit(
                operation=operation,  # type: ignore[arg-type]
                paragraph_id=paragraph_id,
                new_text=new_text.strip(),
            )
        )

    return ChapterRewritePlan(edits=edits)


def apply_chapter_rewrite_plan(
    original: str,
    plan: ChapterRewritePlan,
    *,
    expansion_ratio_percent: int,
) -> str:
    if not plan.edits:
        raise ValueError("章节改写计划 edits 必须是非空列表")
    if not 1 <= expansion_ratio_percent <= 100:
        raise ValueError("章节扩写比例必须在 1 到 100 之间")

    paragraphs = split_chapter_rewrite_paragraphs(original)
    paragraph_by_id = {paragraph.id: paragraph for paragraph in paragraphs}
    edits_by_id = {edit.paragraph_id: edit for edit in plan.edits}

    missing = [paragraph_id for paragraph_id in edits_by_id if paragraph_id not in paragraph_by_id]
    if missing:
        raise ValueError(f"章节改写计划 paragraph_id 不存在: {', '.join(missing)}")

    pieces: list[str] = []
    cursor = 0
    for paragraph in paragraphs:
        pieces.append(original[cursor : paragraph.start])
        edit = edits_by_id.get(paragraph.id)
        if edit is None:
            pieces.append(original[paragraph.start : paragraph.end])
        elif edit.operation == "replace":
            pieces.append(edit.new_text)
        else:
            pieces.append(original[paragraph.start : paragraph.end])
            pieces.append(_insertion_separator(original[paragraph.end :], edit.new_text))
            pieces.append(edit.new_text)
        cursor = paragraph.end
    pieces.append(original[cursor:])
    synthesized = "".join(pieces)
    validate_chapter_rewrite_growth(
        original=original,
        synthesized=synthesized,
        expansion_ratio_percent=expansion_ratio_percent,
    )
    return synthesized


def synthesize_chapter_rewrite_plan(
    *,
    original: str,
    front_matter_markdown: str,
    expansion_ratio_percent: int,
) -> str:
    plan = parse_chapter_rewrite_plan(front_matter_markdown)
    return apply_chapter_rewrite_plan(
        original,
        plan,
        expansion_ratio_percent=expansion_ratio_percent,
    )


def validate_chapter_rewrite_growth(
    *,
    original: str,
    synthesized: str,
    expansion_ratio_percent: int,
) -> None:
    original_length = len(original)
    target_growth = original_length * expansion_ratio_percent / 100
    lower_bound = math.floor(target_growth * 0.8)
    growth = len(synthesized) - original_length
    if growth < lower_bound:
        raise ValueError(
            "章节改写扩写字数低于预算: "
            f"目标增长约 {target_growth:.0f} 字，至少 {lower_bound} 字，实际 {growth} 字"
        )


def _append_rewrite_paragraph(
    paragraphs: list[ChapterRewriteParagraph],
    original: str,
    start: int,
    end: int,
    paragraph_index: int,
) -> int:
    raw = original[start:end]
    if not raw.strip():
        return end
    leading_whitespace = len(raw) - len(raw.lstrip())
    trailing_whitespace = len(raw) - len(raw.rstrip())
    text_start = start + leading_whitespace
    text_end = end - trailing_whitespace
    paragraphs.append(
        ChapterRewriteParagraph(
            id=f"P{paragraph_index:03d}",
            text=original[text_start:text_end],
            start=text_start,
            end=text_end,
            index=paragraph_index,
        )
    )
    return end


def _required_string(raw_edit: dict[Any, Any], key: str, index: int) -> str:
    value = raw_edit.get(key)
    if key == "paragraph_id" and value is not None and not isinstance(value, str):
        return str(value).strip()
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"章节改写计划 Edit {index} 缺少 {key}")
    return value.strip()


def _insertion_separator(after_anchor: str, new_text: str) -> str:
    if after_anchor.startswith("\n\n"):
        return "\n\n"
    if new_text.startswith("\n"):
        return ""
    return "\n\n"
