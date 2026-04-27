from __future__ import annotations

import codecs
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Literal, TypedDict

from app.core.domain_errors import UnprocessableEntityError


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
    sample = sample[:16384]

    for encoding in candidates:
        try:
            sample.decode(encoding, errors="strict")
            return encoding
        except UnicodeDecodeError as exc:
            if exc.reason == "unexpected end of data" and exc.end >= len(sample) - 4:
                return encoding
            continue
        except UnicodeError:
            continue

    try:
        import chardet
        result = chardet.detect(sample)
        if result and result.get("encoding") and result.get("confidence", 0) > 0.5:
            encoding = str(result["encoding"])
            normalized = encoding.lower().replace("_", "-")
            if normalized.startswith("utf-16") and not sample.startswith(
                (b"\xff\xfe", b"\xfe\xff")
            ):
                if b"\x00" not in sample:
                    raise ValueError("ignore utf-16 without BOM")
            return encoding
    except ImportError:
        pass
    except ValueError:
        pass

    return "utf-8"


async def clean_and_decode_upload(
    upload_file,
    max_bytes: int = 0,
) -> AsyncIterator[bytes]:
    first_chunk = await upload_file.read(1024 * 1024)
    if not first_chunk:
        raise UnprocessableEntityError("上传的 TXT 文件为空")

    total_bytes_in = len(first_chunk)
    if max_bytes and total_bytes_in > max_bytes:
        raise UnprocessableEntityError("上传的 TXT 文件过大")

    encoding_candidates = (
        "utf-8-sig",
        "utf-8",
        "gb18030",
        "utf-16",
        "utf-16-le",
        "utf-16-be",
    )
    if first_chunk.startswith(b"\xef\xbb\xbf"):
        encoding = "utf-8-sig"
    elif first_chunk.startswith((b"\xff\xfe", b"\xfe\xff")):
        encoding = "utf-16"
    else:
        encoding = detect_encoding(first_chunk, encoding_candidates)

    decoder = codecs.getincrementaldecoder(encoding)(errors="strict")

    try:
        text_chunk = decoder.decode(first_chunk)
        if text_chunk:
            yield text_chunk.encode("utf-8")

        while True:
            chunk = await upload_file.read(1024 * 1024)
            if not chunk:
                break
            total_bytes_in += len(chunk)
            if max_bytes and total_bytes_in > max_bytes:
                raise UnprocessableEntityError("上传的 TXT 文件过大")

            text_chunk = decoder.decode(chunk)
            if text_chunk:
                yield text_chunk.encode("utf-8")

        final_text = decoder.decode(b"", final=True)
        if final_text:
            yield final_text.encode("utf-8")
    except UnicodeDecodeError as exc:
        raise UnprocessableEntityError(
            "无法识别 TXT 文件编码，请使用 UTF-8 或 GB18030 保存后重试"
        ) from exc


async def read_chunks_and_classification(
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

    total_char_count = 0
    emitted_chunk_count = 0
    sample_buf: list[str] = []
    SAMPLE_LIMIT = 200

    chapter_patterns = [
        re.compile(r"^\s*第[零一二三四五六七八九十百千万0-9]+[章节卷回折][\s　]*.*$"),
        re.compile(r"^\s*Chapter\s*\d+\s*.*$", re.IGNORECASE),
        re.compile(r"^\s*\d+[\.、]\s+.*$"),
    ]
    _TIMESTAMP_RE = re.compile(r"(?:\[|\()\d{1,2}:\d{2}(?::\d{2})?(?:\]|\))|^\d{1,2}:\d{2}", re.MULTILINE)
    _SPEAKER_RE = re.compile(r"^[A-Z][A-Za-z ]{0,20}[:：]|^[一-龥]{1,6}[:：]", re.MULTILINE)
    _NOISE_RE = re.compile(r"\[(?:pauses?|laughs?|inaudible|静默|笑|背景音)\]", re.IGNORECASE)

    def is_chapter_header(line: str) -> bool:
        stripped = line.strip()
        if len(stripped) > 50:
            return False
        if stripped.endswith(("。", "！", "？", ".", "!", "?")):
            return False
        if (stripped.startswith(("“", '"', "‘", "'")) and
            stripped.endswith(("”", '"', "’", "'"))):
            return False

        for pattern in chapter_patterns:
            if pattern.match(line):
                return True
        return False

    current_chunk_lines: list[str] = []
    current_chunk_char_count = 0

    async def emit_chunk() -> None:
        nonlocal current_chunk_lines, current_chunk_char_count, emitted_chunk_count
        if not current_chunk_lines:
            return
        chunk_text = "\n".join(current_chunk_lines).strip()
        if not chunk_text:
            current_chunk_lines = []
            current_chunk_char_count = 0
            return

        if on_chunk is not None:
            await on_chunk(emitted_chunk_count, chunk_text)
        emitted_chunk_count += 1
        current_chunk_lines = []
        current_chunk_char_count = 0

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
            total_char_count += len(stripped)
            if len(sample_buf) < SAMPLE_LIMIT:
                sample_buf.append(stripped)

        if is_chapter_header(line) or current_chunk_char_count > 15000:
            if current_chunk_char_count > 50:
                await emit_chunk()

        current_chunk_lines.append(line)
        current_chunk_char_count += len(stripped)

    await emit_chunk()

    sample_text = "\n".join(sample_buf)
    has_timestamps = bool(_TIMESTAMP_RE.search(sample_text))
    has_speaker_labels = bool(_SPEAKER_RE.search(sample_text))
    has_noise_markers = bool(_NOISE_RE.search(sample_text))
    text_type: Literal["混合文本", "口语字幕", "章节正文"]
    if has_timestamps or has_speaker_labels:
        text_type = "口语字幕" if has_timestamps else "混合文本"
        location_indexing: Literal["时间戳", "章节或段落位置", "无法定位"] = (
            "时间戳" if has_timestamps else "章节或段落位置"
        )
    else:
        text_type = "章节正文"
        location_indexing = "章节或段落位置"

    classification = {
        "text_type": text_type,
        "has_timestamps": has_timestamps,
        "has_speaker_labels": has_speaker_labels,
        "has_noise_markers": has_noise_markers,
        "uses_batch_processing": False,
        "location_indexing": location_indexing,
        "noise_notes": (
            "检测到对话/语气/背景音标记。" if has_noise_markers else "未发现显著噪声。"
        ),
    }
    return emitted_chunk_count, total_char_count, classification
