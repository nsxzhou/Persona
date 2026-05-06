from __future__ import annotations

from collections.abc import AsyncIterator

from app.core.domain_errors import UnprocessableEntityError
from app.core.text_processing import clean_and_decode_upload


def ensure_txt_upload_filename(filename: str | None) -> str:
    normalized = (filename or "").strip()
    if not normalized.lower().endswith(".txt"):
        raise UnprocessableEntityError("仅支持上传 .txt 样本文件")
    return normalized


def clean_txt_upload_stream(upload_file, *, max_bytes: int) -> AsyncIterator[bytes]:
    return clean_and_decode_upload(upload_file, max_bytes=max_bytes)
