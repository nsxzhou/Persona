from __future__ import annotations

import re

_STRUCTURAL_PREFIX_RE = re.compile(r"^\s{0,3}#{1,6}\s+")
_SEPARATOR_RE = re.compile(r"^(?:-{3,}|={3,}|\*{3,}|·{3,}|…{3,})$")
_LIST_PREFIX_RE = re.compile(r"^\s*(?:[-*+•]\s*|(?:\d+|[一二三四五六七八九十]+)[.)、]\s*)")
_SQUARE_LABEL_RE = re.compile(r"^\[(?P<label>[^\]\n]{1,80})\]\s*(?P<body>.+?)\s*$")
_FULLWIDTH_LABEL_RE = re.compile(r"^【(?P<label>[^】\n]{1,80})】\s*(?P<body>.+?)\s*$")

_INTRO_PREFIXES = (
    "以下是",
    "如下",
    "下面是",
    "接下来是",
    "节拍如下",
    "节拍列表",
    "生成如下",
    "请生成",
    "请看",
    "说明：",
    "备注：",
    "注：",
    "注意：",
    "附：",
    "提示：",
)


def _is_structural_noise(line: str) -> bool:
    if not line:
        return True
    if line.startswith("```"):
        return True
    if line.startswith(">"):
        return True
    if _STRUCTURAL_PREFIX_RE.match(line):
        return True
    if _SEPARATOR_RE.match(line):
        return True
    return False


def _strip_list_prefix(line: str) -> tuple[str, bool]:
    stripped = _LIST_PREFIX_RE.sub("", line).strip()
    return stripped, stripped != line.strip()


def _normalize_beat_line(line: str) -> str | None:
    candidate = line.strip().lstrip("\ufeff")
    if not candidate or _is_structural_noise(candidate):
        return None

    candidate, _ = _strip_list_prefix(candidate)
    if not candidate:
        return None

    square_match = _SQUARE_LABEL_RE.match(candidate)
    if square_match:
        body = square_match.group("body").strip()
        if not body:
            return None
        label = square_match.group("label").strip()
        return f"[{label}] {body}"

    fullwidth_match = _FULLWIDTH_LABEL_RE.match(candidate)
    if fullwidth_match:
        body = fullwidth_match.group("body").strip()
        if not body:
            return None
        label = fullwidth_match.group("label").strip()
        return f"[{label}] {body}"

    if any(candidate.startswith(prefix) for prefix in _INTRO_PREFIXES):
        return None

    return candidate


def parse_beats_markdown(markdown: str) -> list[str]:
    if markdown.strip() == "":
        return []

    explicit_beats: list[str] = []
    bullet_beats: list[str] = []
    plain_beats: list[str] = []

    for raw_line in markdown.splitlines():
        normalized = _normalize_beat_line(raw_line)
        if normalized is None:
            continue

        stripped_line = raw_line.strip()
        if _LIST_PREFIX_RE.match(stripped_line):
            if normalized.startswith("[") or normalized.startswith("【"):
                explicit_beats.append(normalized)
            else:
                bullet_beats.append(normalized)
            continue

        if normalized.startswith("[") or normalized.startswith("【"):
            explicit_beats.append(normalized)
        else:
            plain_beats.append(normalized)

    if explicit_beats:
        return explicit_beats
    if bullet_beats:
        return bullet_beats
    return plain_beats
