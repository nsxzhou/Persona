from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
from collections.abc import AsyncIterator
from pathlib import Path

import aiofiles
from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings


class StyleAnalysisStorageService:
    def _storage_root(self) -> Path:
        return Path(get_settings().storage_dir).expanduser()

    def _build_storage_path(self, sample_file_id: str) -> Path:
        return self._storage_root() / "style-samples" / f"{sample_file_id}.txt"

    def _job_artifact_dir(self, job_id: str) -> Path:
        return self._storage_root() / "style-analysis-artifacts" / job_id

    def _chunk_artifact_path(self, job_id: str, chunk_index: int) -> Path:
        return self._job_artifact_dir(job_id) / "chunks" / f"{chunk_index:06d}.txt"

    def _chunk_analysis_artifact_path(self, job_id: str, chunk_index: int) -> Path:
        return self._job_artifact_dir(job_id) / "chunk-analyses" / f"{chunk_index:06d}.json"

    async def stream_file(self, sample_file_id: str) -> AsyncIterator[bytes]:
        storage_path = self._build_storage_path(sample_file_id)
        if not storage_path.exists():
            raise FileNotFoundError(f"Sample file {sample_file_id} not found at {storage_path}")
        async with aiofiles.open(storage_path, "rb") as handle:
            while chunk := await handle.read(64 * 1024):
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
            storage_path.unlink(missing_ok=True)
            raise

        if total_bytes == 0:
            storage_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="上传的 TXT 文件为空",
            )

        return str(storage_path), total_bytes, hasher.hexdigest()

    async def write_chunk_artifact(
        self,
        job_id: str,
        chunk_index: int,
        chunk_text: str,
    ) -> None:
        path = self._chunk_artifact_path(job_id, chunk_index)
        path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(path, "w", encoding="utf-8") as handle:
            await handle.write(chunk_text)

    async def read_chunk_artifact(
        self,
        job_id: str,
        chunk_index: int,
    ) -> str:
        path = self._chunk_artifact_path(job_id, chunk_index)
        async with aiofiles.open(path, "r", encoding="utf-8") as handle:
            return await handle.read()

    async def write_chunk_analysis_artifact(
        self,
        job_id: str,
        chunk_index: int,
        payload: dict,
    ) -> None:
        path = self._chunk_analysis_artifact_path(job_id, chunk_index)
        path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(path, "w", encoding="utf-8") as handle:
            await handle.write(json.dumps(payload, ensure_ascii=False))

    async def read_chunk_analysis_batches(
        self,
        job_id: str,
        *,
        batch_size: int,
    ) -> AsyncIterator[list[dict]]:
        analysis_dir = self._job_artifact_dir(job_id) / "chunk-analyses"
        if not analysis_dir.exists():
            return

        paths = sorted(analysis_dir.glob("*.json"))
        batch: list[dict] = []
        for path in paths:
            async with aiofiles.open(path, "r", encoding="utf-8") as handle:
                batch.append(json.loads(await handle.read()))
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

    async def cleanup_job_artifacts(self, job_id: str) -> None:
        artifact_dir = self._job_artifact_dir(job_id)
        if artifact_dir.exists():
            await asyncio.to_thread(shutil.rmtree, artifact_dir, ignore_errors=True)

    async def job_artifacts_exist(self, job_id: str) -> bool:
        return self._job_artifact_dir(job_id).exists()
