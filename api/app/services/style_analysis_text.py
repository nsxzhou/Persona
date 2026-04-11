from __future__ import annotations

import codecs
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Literal, TypedDict


class InputClassification(TypedDict):
    text_type: Literal["混合文本", "口语字幕", "章节正文"]
    has_timestamps: bool
    has_speaker_labels: bool
    has_noise_markers: bool
    uses_batch_processing: bool
    location_indexing: Literal["时间戳", "章节或段落位置", "无法定位"]
    noise_notes: str


ChunkConsumer = Callable[[int, str], Awaitable[None]]


def detect_encoding(sample: bytes, candidates: tuple[str, ...]) -> str:
    sample = sample[:8192]
    for encoding in candidates:
        try:
            sample.decode(encoding)
        except UnicodeDecodeError:
            continue
        return encoding
    raise RuntimeError("TXT 文件编码无法识别，请改为 UTF-8 后重试")


async def read_chunks_and_classification(
    stream: AsyncIterator[bytes],
    *,
    chunk_size: int,
    encoding_candidates: tuple[str, ...] = ("utf-8-sig", "utf-8", "gb18030"),
    on_chunk: ChunkConsumer | None = None,
) -> tuple[int, int, InputClassification]:
    try:
        first_chunk = await anext(stream)
    except StopAsyncIteration:
        first_chunk = b""

    if not first_chunk:
        classification: InputClassification = {
            "text_type": "章节正文",
            "has_timestamps": False,
            "has_speaker_labels": False,
            "has_noise_markers": False,
            "uses_batch_processing": False,
            "location_indexing": "无法定位",
            "noise_notes": "未发现显著噪声。",
        }
        return 0, 0, classification

    encoding = detect_encoding(first_chunk, encoding_candidates)
    decoder = codecs.getincrementaldecoder(encoding)(errors="strict")

    has_timestamps = False
    has_speaker_labels = False
    has_noise_markers = False
    saw_paragraph_break = False
    total_char_count = 0
    emitted_chunk_count = 0

    ts_pattern = re.compile(
        r"^\s*(\d{1,2}:\d{2}(?::\d{2})?|\[\d{1,2}:\d{2}(?::\d{2})?\])"
    )
    speaker_pattern = re.compile(r"^[^\n：:]{1,20}[：:]")
    noise_pattern = re.compile(r"(\[.*?\]|（.*?笑.*?）|【.*?】)")

    current_chunk_parts: list[str] = []
    current_chunk_length = 0
    paragraph_lines: list[str] = []
    have_paragraph_content = False

    async def emit_chunk() -> None:
        nonlocal current_chunk_parts, current_chunk_length, emitted_chunk_count
        if not current_chunk_parts:
            return
        chunk_text = "\n\n".join(current_chunk_parts)
        if on_chunk is not None:
            await on_chunk(emitted_chunk_count, chunk_text)
        emitted_chunk_count += 1
        current_chunk_parts = []
        current_chunk_length = 0

    async def flush_paragraph() -> None:
        nonlocal current_chunk_parts, current_chunk_length, total_char_count, paragraph_lines
        paragraph = "\n".join(paragraph_lines).replace("\x00", "").strip()
        paragraph_lines = []
        if not paragraph:
            return
        paragraph_length = len(paragraph)
        total_char_count += paragraph_length
        if current_chunk_parts and current_chunk_length + paragraph_length + 2 > chunk_size:
            await emit_chunk()
        if current_chunk_parts:
            current_chunk_length += 2
            total_char_count += 2
        current_chunk_parts.append(paragraph)
        current_chunk_length += paragraph_length

    async def line_generator() -> AsyncIterator[str]:
        buffer = ""
        text_chunk = decoder.decode(first_chunk)
        buffer += text_chunk.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")

        lines = buffer.split("\n")
        buffer = lines.pop()
        for line in lines:
            yield line

        async for chunk in stream:
            text_chunk = decoder.decode(chunk)
            buffer += text_chunk.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")

            lines = buffer.split("\n")
            buffer = lines.pop()
            for line in lines:
                yield line

        final_text = decoder.decode(b"", final=True)
        buffer += final_text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
        if buffer:
            yield buffer

    async for line in line_generator():
        stripped = line.strip()
        if stripped:
            have_paragraph_content = True
            if not has_timestamps and ts_pattern.match(line):
                has_timestamps = True
            if not has_speaker_labels and speaker_pattern.match(line):
                has_speaker_labels = True
            if not has_noise_markers and noise_pattern.search(line):
                has_noise_markers = True
            paragraph_lines.append(line)
            continue

        if have_paragraph_content:
            await flush_paragraph()
            saw_paragraph_break = True
            have_paragraph_content = False

    if have_paragraph_content:
        await flush_paragraph()

    if current_chunk_parts:
        await emit_chunk()

    if has_timestamps and has_speaker_labels:
        text_type: Literal["混合文本", "口语字幕", "章节正文"] = "混合文本"
    elif has_timestamps:
        text_type = "口语字幕"
    else:
        text_type = "章节正文"

    if has_timestamps:
        location_indexing: Literal["时间戳", "章节或段落位置", "无法定位"] = "时间戳"
    elif saw_paragraph_break:
        location_indexing = "章节或段落位置"
    else:
        location_indexing = "无法定位"

    classification: InputClassification = {
        "text_type": text_type,
        "has_timestamps": has_timestamps,
        "has_speaker_labels": has_speaker_labels,
        "has_noise_markers": has_noise_markers,
        "uses_batch_processing": False,
        "location_indexing": location_indexing,
        "noise_notes": "检测到显著噪声标记。" if has_noise_markers else "未发现显著噪声。",
    }
    return emitted_chunk_count, total_char_count, classification
