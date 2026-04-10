from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator
from pathlib import Path

import aiofiles
from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings


class StyleAnalysisStorageService:
    def _build_storage_path(self, sample_file_id: str) -> Path:
        settings = get_settings()
        return Path(settings.storage_dir).expanduser() / "style-samples" / f"{sample_file_id}.txt"

    async def stream_file(self, sample_file_id: str) -> AsyncIterator[bytes]:
        storage_path = self._build_storage_path(sample_file_id)
        if not storage_path.exists():
            raise FileNotFoundError(f"Sample file {sample_file_id} not found at {storage_path}")
        async with aiofiles.open(storage_path, "rb") as f:
            while chunk := await f.read(64 * 1024):
                yield chunk

    async def save_file(
        self,
        sample_file_id: str,
        upload_file: UploadFile,
    ) -> tuple[str, int, str]:
        storage_path = self._build_storage_path(sample_file_id)
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        settings = get_settings()
        max_bytes = getattr(settings, "style_analysis_max_upload_bytes", 0) or 0
        hasher = hashlib.sha256()
        total_bytes = 0

        try:
            async with aiofiles.open(storage_path, "wb") as handle:
                while True:
                    chunk = await upload_file.read(1024 * 1024)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if max_bytes and total_bytes > max_bytes:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                            detail="上传的 TXT 文件过大",
                        )
                    hasher.update(chunk)
                    await handle.write(chunk)
        except Exception:
            if storage_path.exists():
                storage_path.unlink(missing_ok=True)
            raise

        if total_bytes == 0:
            if storage_path.exists():
                storage_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="上传的 TXT 文件为空",
            )

        return str(storage_path), total_bytes, hasher.hexdigest()
