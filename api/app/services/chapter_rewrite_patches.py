from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Literal


ChapterRewritePatchOperation = Literal["insert_after", "replace"]

_PATCH_HEADING_RE = re.compile(
    r"(?ms)^##\s+Patch\s+\d+\s*$"
    r"(?P<body>.*?)(?=^##\s+Patch\s+\d+\s*$|\Z)"
)
_EDIT_HEADING_RE = re.compile(
    r"(?ms)^###\s+Edit\s+\d+\s*$"
    r"(?P<body>.*?)(?=^###\s+Edit\s+\d+\s*$|\Z)"
)
_OPERATION_RE = re.compile(r"(?mi)^\s*Operation:\s*(?P<operation>\S+)\s*$")
_ANCHOR_BLOCK_RE = re.compile(
    r"(?ms)^\s*Anchor:\s*\n```text\s*\n(?P<anchor>.*?)\n```\s*"
)
_NEW_TEXT_BLOCK_RE = re.compile(
    r"(?ms)^\s*New Text:\s*\n```text\s*\n(?P<new_text>.*?)\n```\s*"
)
_NO_PATCHES_RE = re.compile(r"(?ms)^# Chapter Rewrite Patches\s+No patches\.\s*$")


@dataclass(frozen=True)
class ChapterRewritePatch:
    operation: ChapterRewritePatchOperation
    anchor: str
    new_text: str


@dataclass(frozen=True)
class _LocatedPatch:
    patch: ChapterRewritePatch
    start: int
    end: int
    anchor_index: int


def parse_chapter_rewrite_patches(markdown: str) -> list[ChapterRewritePatch]:
    stripped = markdown.strip()
    if not stripped:
        raise ValueError("章节改写补丁输出为空")
    if _NO_PATCHES_RE.fullmatch(stripped):
        raise ValueError("章节改写未返回任何可用补丁")

    matches = list(_PATCH_HEADING_RE.finditer(stripped))
    if not matches:
        raise ValueError("章节改写补丁输出缺少 Patch 小节")

    patches: list[ChapterRewritePatch] = []
    consumed_ranges: list[tuple[int, int]] = []
    for match in matches:
        body = match.group("body")
        if not body.strip():
            raise ValueError("章节改写 Patch 小节为空")

        edit_matches = list(_EDIT_HEADING_RE.finditer(body))
        if not edit_matches:
            if (
                _OPERATION_RE.search(body) is not None
                or "Anchor:" in body
                or "New Text:" in body
            ):
                raise ValueError(
                    "章节改写 Patch 必须包含至少一个 ### Edit 小节；"
                    "旧版直接在 Patch 下写 Operation/Anchor/New Text 的格式不再支持"
                )
            raise ValueError("章节改写 Patch 缺少 ### Edit 小节")
        if body[: edit_matches[0].start()].strip():
            raise ValueError("章节改写 Patch 包含无法识别的内容")

        for edit_match in edit_matches:
            edit_body = edit_match.group("body")
            if not edit_body.strip():
                raise ValueError("章节改写 Edit 小节为空")

            operation_match = _OPERATION_RE.search(edit_body)
            if operation_match is None:
                raise ValueError("章节改写 Edit 缺少 Operation")
            if edit_body[: operation_match.start()].strip():
                raise ValueError("章节改写 Edit 包含无法识别的内容")
            operation = operation_match.group("operation").strip()
            if operation not in {"insert_after", "replace"}:
                raise ValueError(f"章节改写 Edit 操作不支持: {operation}")

            search_start = operation_match.end()
            anchor_match = _ANCHOR_BLOCK_RE.search(edit_body, search_start)
            if anchor_match is None:
                raise ValueError("章节改写 Edit 缺少 Anchor 代码块")
            if edit_body[operation_match.end() : anchor_match.start()].strip():
                raise ValueError("章节改写 Edit 包含无法识别的内容")
            new_text_match = _NEW_TEXT_BLOCK_RE.search(edit_body, anchor_match.end())
            if new_text_match is None:
                raise ValueError("章节改写 Edit 缺少 New Text 代码块")
            if edit_body[anchor_match.end() : new_text_match.start()].strip():
                raise ValueError("章节改写 Edit 包含无法识别的内容")

            tail = edit_body[new_text_match.end() :].strip()
            if tail:
                raise ValueError("章节改写 Edit 包含无法识别的内容")

            anchor = anchor_match.group("anchor").strip()
            new_text = new_text_match.group("new_text").strip()
            if not anchor:
                raise ValueError("章节改写 Edit Anchor 不能为空")
            if not new_text:
                raise ValueError("章节改写 Edit New Text 不能为空")

            patches.append(
                ChapterRewritePatch(
                    operation=operation,  # type: ignore[arg-type]
                    anchor=anchor,
                    new_text=new_text,
                )
            )
        consumed_ranges.append((match.start(), match.end()))

    prefix = stripped[: consumed_ranges[0][0]].strip()
    suffix = stripped[consumed_ranges[-1][1] :].strip()
    if prefix != "# Chapter Rewrite Patches":
        raise ValueError("章节改写补丁输出标题不符合契约")
    if suffix:
        raise ValueError("章节改写补丁输出包含 Patch 小节之外的内容")
    return patches


def apply_chapter_rewrite_patches(
    original: str,
    patches: list[ChapterRewritePatch],
    *,
    expansion_ratio_percent: int,
) -> str:
    if not patches:
        raise ValueError("章节改写补丁列表为空")
    if not 1 <= expansion_ratio_percent <= 100:
        raise ValueError("章节扩写比例必须在 1 到 100 之间")

    located = _locate_patches(original, patches)
    pieces: list[str] = []
    cursor = 0
    for item in located:
        pieces.append(original[cursor : item.start])
        if item.patch.operation == "replace":
            pieces.append(item.patch.new_text)
        else:
            pieces.append(original[item.start : item.end])
            pieces.append(_insertion_separator(original[item.end :], item.patch.new_text))
            pieces.append(item.patch.new_text)
        cursor = item.end
    pieces.append(original[cursor:])
    synthesized = "".join(pieces)
    validate_chapter_rewrite_growth(
        original=original,
        synthesized=synthesized,
        expansion_ratio_percent=expansion_ratio_percent,
    )
    return synthesized


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


def _locate_patches(
    original: str,
    patches: list[ChapterRewritePatch],
) -> list[_LocatedPatch]:
    located: list[_LocatedPatch] = []
    seen_anchors: set[str] = set()
    for patch in patches:
        if patch.anchor in seen_anchors:
            raise ValueError("章节改写补丁重复使用同一 Anchor")
        seen_anchors.add(patch.anchor)

        start = original.find(patch.anchor)
        if start < 0:
            raise ValueError("章节改写补丁 Anchor 未在原章节中找到")
        if original.find(patch.anchor, start + len(patch.anchor)) >= 0:
            raise ValueError("章节改写补丁 Anchor 在原章节中出现多次")
        end = start + len(patch.anchor)
        if not _is_complete_natural_paragraph(original, start, end):
            raise ValueError("章节改写补丁 Anchor 必须是完整自然段")
        if _contains_paragraph_break(patch.anchor):
            raise ValueError("章节改写补丁 Anchor 只能定位一个自然段")
        located.append(
            _LocatedPatch(
                patch=patch,
                start=start,
                end=end,
                anchor_index=start,
            )
        )

    located.sort(key=lambda item: item.anchor_index)
    for previous, current in zip(located, located[1:]):
        if previous.end > current.start:
            raise ValueError("章节改写补丁 Anchor 存在重叠")
        if (
            previous.patch.anchor in current.patch.anchor
            or current.patch.anchor in previous.patch.anchor
        ):
            raise ValueError("章节改写补丁 Anchor 存在包含关系")
    return located


def _is_complete_natural_paragraph(original: str, start: int, end: int) -> bool:
    return _at_paragraph_boundary_before(original, start) and _at_paragraph_boundary_after(
        original,
        end,
    )


def _at_paragraph_boundary_before(text: str, index: int) -> bool:
    prefix = text[:index]
    return not prefix.strip() or re.search(r"\n[ \t]*\n[ \t]*\Z", prefix) is not None


def _at_paragraph_boundary_after(text: str, index: int) -> bool:
    suffix = text[index:]
    return not suffix.strip() or re.match(r"[ \t]*\n[ \t]*\n", suffix) is not None


def _contains_paragraph_break(text: str) -> bool:
    return re.search(r"\n[ \t]*\n", text.strip()) is not None


def _insertion_separator(after_anchor: str, new_text: str) -> str:
    if after_anchor.startswith("\n\n"):
        return "\n\n"
    if new_text.startswith("\n"):
        return ""
    return "\n\n"
