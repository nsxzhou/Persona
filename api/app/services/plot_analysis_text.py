from __future__ import annotations

import codecs
import logging
import re
from dataclasses import dataclass
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import TypedDict

from app.core.config import get_settings
from app.core.text_processing import ChunkConsumer, InputClassification, detect_encoding

logger = logging.getLogger(__name__)


class PlotChunkManifestEntry(TypedDict):
    index: int
    start_paragraph: int
    end_paragraph: int
    primary_char_count: int
    overlap_before_chars: int
    overlap_after_chars: int


PlotBoundaryDetector = Callable[[list[str]], Awaitable[list[int] | None]]


_CHAPTER_PATTERNS = [
    re.compile(r"^\s*第[零一二三四五六七八九十百千万0-9]+[章节卷回折][\s　]*.*$"),
    re.compile(r"^\s*Chapter\s*\d+\s*.*$", re.IGNORECASE),
    re.compile(r"^\s*\d+[\.、]\s+.*$"),
]
_TIMESTAMP_RE = re.compile(r"(?:\[|\()\d{1,2}:\d{2}(?::\d{2})?(?:\]|\))|^\d{1,2}:\d{2}", re.MULTILINE)
_SPEAKER_RE = re.compile(r"^[A-Z][A-Za-z ]{0,20}[:：]|^[一-龥]{1,6}[:：]", re.MULTILINE)
_NOISE_RE = re.compile(r"\[(?:pauses?|laughs?|inaudible|静默|笑|背景音)\]", re.IGNORECASE)
_SEPARATOR_RE = re.compile(r"^[=\-*_~#·•]{3,}$")


@dataclass(frozen=True)
class _ParagraphSpan:
    start_paragraph: int
    end_paragraph: int
    paragraphs: list[str]
    starts_at_hard_boundary: bool

    @property
    def char_count(self) -> int:
        return sum(_paragraph_char_count(paragraph) for paragraph in self.paragraphs)


def _empty_classification() -> InputClassification:
    return {
        "text_type": "章节正文",
        "has_timestamps": False,
        "has_speaker_labels": False,
        "has_noise_markers": False,
        "uses_batch_processing": False,
        "location_indexing": "无法定位",
        "noise_notes": "未发现显著噪声。",
    }


def _paragraph_char_count(paragraph: str) -> int:
    return len("".join(line.strip() for line in paragraph.splitlines() if line.strip()))


def _normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")


def _split_paragraphs(text: str) -> list[str]:
    return [paragraph.strip() for paragraph in re.split(r"\n\s*\n+", text) if paragraph.strip()]


def _is_chapter_header(text: str) -> bool:
    stripped = text.strip()
    if not stripped or "\n" in stripped or len(stripped) > 50:
        return False
    if stripped.endswith(("。", "！", "？", ".", "!", "?")):
        return False
    if stripped.startswith(("“", '"', "‘", "'")) and stripped.endswith(("”", '"', "’", "'")):
        return False
    return any(pattern.match(stripped) for pattern in _CHAPTER_PATTERNS)


def _looks_like_scene_title(text: str) -> bool:
    stripped = text.strip()
    if not stripped or "\n" in stripped:
        return False
    if len(stripped) > 24:
        return False
    if stripped.endswith(("。", "！", "？", ".", "!", "?")):
        return False
    return (
        "场景" in stripped
        or stripped.startswith(("Scene", "SCENE", "地点", "时间", "转场"))
        or "：" in stripped
        or ":" in stripped
    )


def _is_hard_boundary(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    return _is_chapter_header(stripped) or bool(_SEPARATOR_RE.fullmatch(stripped)) or _looks_like_scene_title(stripped)


def _classify_text(sample_lines: list[str]) -> InputClassification:
    sample_text = "\n".join(sample_lines)
    has_timestamps = bool(_TIMESTAMP_RE.search(sample_text))
    has_speaker_labels = bool(_SPEAKER_RE.search(sample_text))
    has_noise_markers = bool(_NOISE_RE.search(sample_text))
    if has_timestamps or has_speaker_labels:
        text_type = "口语字幕" if has_timestamps else "混合文本"
        location_indexing = "时间戳" if has_timestamps else "章节或段落位置"
    else:
        text_type = "章节正文"
        location_indexing = "章节或段落位置"
    return {
        "text_type": text_type,
        "has_timestamps": has_timestamps,
        "has_speaker_labels": has_speaker_labels,
        "has_noise_markers": has_noise_markers,
        "uses_batch_processing": False,
        "location_indexing": location_indexing,
        "noise_notes": "检测到对话/语气/背景音标记。" if has_noise_markers else "未发现显著噪声。",
    }


async def _read_text(stream: AsyncIterator[bytes], encoding_candidates: tuple[str, ...]) -> str:
    try:
        first_chunk = await anext(stream)
    except StopAsyncIteration:
        return ""
    if not first_chunk:
        return ""
    encoding = detect_encoding(first_chunk, encoding_candidates)
    decoder = codecs.getincrementaldecoder(encoding)(errors="strict")
    pieces = [_normalize_text(decoder.decode(first_chunk))]
    async for chunk in stream:
        pieces.append(_normalize_text(decoder.decode(chunk)))
    pieces.append(_normalize_text(decoder.decode(b"", final=True)))
    return "".join(pieces)


def _build_initial_spans(paragraphs: list[str]) -> list[_ParagraphSpan]:
    spans: list[_ParagraphSpan] = []
    current_start = 0
    current_paragraphs: list[str] = []
    current_hard_boundary = True
    for index, paragraph in enumerate(paragraphs):
        if current_paragraphs and _is_hard_boundary(paragraph):
            spans.append(
                _ParagraphSpan(
                    start_paragraph=current_start,
                    end_paragraph=index,
                    paragraphs=current_paragraphs,
                    starts_at_hard_boundary=current_hard_boundary,
                )
            )
            current_start = index
            current_paragraphs = [paragraph]
            current_hard_boundary = True
            continue
        current_paragraphs.append(paragraph)
    if current_paragraphs:
        spans.append(
            _ParagraphSpan(
                start_paragraph=current_start,
                end_paragraph=len(paragraphs),
                paragraphs=current_paragraphs,
                starts_at_hard_boundary=current_hard_boundary,
            )
        )
    return spans


def _make_span(
    start_paragraph: int,
    paragraphs: list[str],
    *,
    starts_at_hard_boundary: bool,
) -> _ParagraphSpan:
    return _ParagraphSpan(
        start_paragraph=start_paragraph,
        end_paragraph=start_paragraph + len(paragraphs),
        paragraphs=paragraphs,
        starts_at_hard_boundary=starts_at_hard_boundary,
    )


def _split_text_by_sentence(text: str, *, target_chars: int, max_chars: int) -> list[str]:
    sentences = [part.strip() for part in re.split(r"(?<=[。！？!?；;])", text) if part.strip()]
    if not sentences:
        sentences = [text.strip()]
    segments: list[str] = []
    current = ""
    for sentence in sentences:
        if not current:
            current = sentence
            continue
        if len(current) + len(sentence) <= target_chars:
            current += sentence
            continue
        segments.append(current)
        current = sentence
    if current:
        segments.append(current)

    sliced: list[str] = []
    for segment in segments:
        if len(segment) <= max_chars:
            sliced.append(segment)
            continue
        for start in range(0, len(segment), max_chars):
            sliced.append(segment[start:start + max_chars])
    return [segment for segment in sliced if segment]


def _split_by_paragraph_fallback(
    span: _ParagraphSpan,
    *,
    min_chars: int,
    target_chars: int,
    max_chars: int,
) -> list[_ParagraphSpan]:
    result: list[_ParagraphSpan] = []
    start = 0
    while start < len(span.paragraphs):
        paragraph_chars = _paragraph_char_count(span.paragraphs[start])
        absolute_start = span.start_paragraph + start
        if paragraph_chars > max_chars:
            parts = _split_text_by_sentence(
                span.paragraphs[start],
                target_chars=target_chars,
                max_chars=max_chars,
            )
            for index, part in enumerate(parts):
                result.append(
                    _make_span(
                        absolute_start + index,
                        [part],
                        starts_at_hard_boundary=(start == 0 and index == 0),
                    )
                )
            start += 1
            continue

        end = start
        chars = 0
        best_end: int | None = None
        best_diff: int | None = None
        while end < len(span.paragraphs):
            next_chars = _paragraph_char_count(span.paragraphs[end])
            if chars + next_chars > max_chars:
                break
            chars += next_chars
            end += 1
            if chars >= min_chars:
                diff = abs(target_chars - chars)
                if best_end is None or diff < best_diff:
                    best_end = end
                    best_diff = diff
        split_end = best_end or end
        if split_end <= start:
            split_end = start + 1
        result.append(
            _make_span(
                absolute_start,
                span.paragraphs[start:split_end],
                starts_at_hard_boundary=(start == 0 and span.starts_at_hard_boundary),
            )
        )
        start = split_end
    return result


def _normalize_detector_boundaries(boundaries: list[int] | None, paragraph_count: int) -> list[int]:
    if not boundaries:
        return []
    normalized = sorted({boundary for boundary in boundaries if 0 < boundary < paragraph_count})
    return normalized


async def _split_oversized_span(
    span: _ParagraphSpan,
    *,
    min_chars: int,
    target_chars: int,
    max_chars: int,
    boundary_detector: PlotBoundaryDetector | None,
) -> list[_ParagraphSpan]:
    if span.char_count <= max_chars:
        return [span]

    if boundary_detector is not None and len(span.paragraphs) > 1:
        try:
            boundaries = _normalize_detector_boundaries(
                await boundary_detector(span.paragraphs),
                len(span.paragraphs),
            )
        except Exception:
            logger.exception("Plot boundary detector failed; falling back to paragraph split")
            boundaries = []
        if boundaries:
            detector_spans: list[_ParagraphSpan] = []
            start = 0
            for boundary in boundaries + [len(span.paragraphs)]:
                detector_spans.append(
                    _make_span(
                        span.start_paragraph + start,
                        span.paragraphs[start:boundary],
                        starts_at_hard_boundary=(start == 0 and span.starts_at_hard_boundary),
                    )
                )
                start = boundary
            if all(detector_span.char_count <= max_chars for detector_span in detector_spans):
                return detector_spans

    return _split_by_paragraph_fallback(
        span,
        min_chars=min_chars,
        target_chars=target_chars,
        max_chars=max_chars,
    )


async def _finalize_spans(
    spans: list[_ParagraphSpan],
    *,
    min_chars: int,
    target_chars: int,
    max_chars: int,
    boundary_detector: PlotBoundaryDetector | None,
) -> list[_ParagraphSpan]:
    finalized: list[_ParagraphSpan] = []
    for span in spans:
        finalized.extend(
            await _split_oversized_span(
                span,
                min_chars=min_chars,
                target_chars=target_chars,
                max_chars=max_chars,
                boundary_detector=boundary_detector,
            )
        )
    return finalized


def _pack_spans_into_chunks(
    spans: list[_ParagraphSpan],
    *,
    min_chars: int,
    target_chars: int,
    max_chars: int,
) -> list[_ParagraphSpan]:
    chunks: list[_ParagraphSpan] = []
    current_paragraphs: list[str] = []
    current_start: int | None = None
    current_chars = 0
    current_hard_boundary = True

    def emit_current() -> None:
        nonlocal current_paragraphs, current_start, current_chars, current_hard_boundary
        if not current_paragraphs or current_start is None:
            return
        chunks.append(
            _make_span(
                current_start,
                current_paragraphs,
                starts_at_hard_boundary=current_hard_boundary,
            )
        )
        current_paragraphs = []
        current_start = None
        current_chars = 0
        current_hard_boundary = True

    for span in spans:
        if current_paragraphs and current_chars >= min_chars:
            if span.starts_at_hard_boundary or current_chars + span.char_count > target_chars:
                emit_current()
        if current_paragraphs and current_chars + span.char_count > max_chars and current_chars >= min_chars:
            emit_current()
        if not current_paragraphs:
            current_start = span.start_paragraph
            current_hard_boundary = span.starts_at_hard_boundary
        current_paragraphs.extend(span.paragraphs)
        current_chars += span.char_count
    emit_current()
    return chunks


def _build_manifest(chunks: list[_ParagraphSpan]) -> list[PlotChunkManifestEntry]:
    settings = get_settings()
    overlap_ratio = settings.plot_analysis_chunk_overlap_ratio
    overlap_cap = 1500
    manifest: list[PlotChunkManifestEntry] = []
    char_counts = [chunk.char_count for chunk in chunks]
    for index, chunk in enumerate(chunks):
        overlap_before = 0
        overlap_after = 0
        requested_overlap = min(int(chunk.char_count * overlap_ratio), overlap_cap)
        if index > 0:
            overlap_before = min(requested_overlap, char_counts[index - 1])
        if index + 1 < len(chunks):
            overlap_after = min(requested_overlap, char_counts[index + 1])
        manifest.append(
            {
                "index": index,
                "start_paragraph": chunk.start_paragraph,
                "end_paragraph": chunk.end_paragraph,
                "primary_char_count": chunk.char_count,
                "overlap_before_chars": overlap_before,
                "overlap_after_chars": overlap_after,
            }
        )
    return manifest


async def read_plot_chunks_and_classification(
    stream: AsyncIterator[bytes],
    *,
    encoding_candidates: tuple[str, ...] = (
        "utf-8-sig",
        "utf-8",
        "gb18030",
        "utf-16",
        "utf-16-le",
        "utf-16-be",
    ),
    on_chunk: ChunkConsumer | None = None,
    boundary_detector: PlotBoundaryDetector | None = None,
) -> tuple[int, int, InputClassification, list[PlotChunkManifestEntry]]:
    text = await _read_text(stream, encoding_candidates)
    if not text.strip():
        return 0, 0, _empty_classification(), []

    normalized_text = _normalize_text(text)
    lines = [line.strip() for line in normalized_text.splitlines() if line.strip()]
    sample_lines = lines[:200]
    classification = _classify_text(sample_lines)
    paragraphs = _split_paragraphs(normalized_text)
    if not paragraphs:
        return 0, 0, _empty_classification(), []

    total_char_count = sum(_paragraph_char_count(paragraph) for paragraph in paragraphs)
    settings = get_settings()
    spans = _build_initial_spans(paragraphs)
    spans = await _finalize_spans(
        spans,
        min_chars=settings.plot_analysis_chunk_min_chars,
        target_chars=settings.plot_analysis_chunk_target_chars,
        max_chars=settings.plot_analysis_chunk_max_chars,
        boundary_detector=boundary_detector,
    )
    chunks = _pack_spans_into_chunks(
        spans,
        min_chars=settings.plot_analysis_chunk_min_chars,
        target_chars=settings.plot_analysis_chunk_target_chars,
        max_chars=settings.plot_analysis_chunk_max_chars,
    )

    if on_chunk is not None:
        for index, chunk in enumerate(chunks):
            await on_chunk(index, "\n\n".join(chunk.paragraphs).strip())

    manifest = _build_manifest(chunks)
    return len(chunks), total_char_count, classification, manifest
