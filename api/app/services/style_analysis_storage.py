from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
from collections.abc import AsyncIterator
from pathlib import Path

import aiofiles

from app.core.config import get_settings
from app.core.domain_errors import UnprocessableEntityError


class StyleAnalysisStorageService:
    def _storage_root(self) -> Path:
        return Path(get_settings().storage_dir).expanduser()

    def _build_storage_path(self, sample_file_id: str) -> Path:
        return self._storage_root() / "style-samples" / f"{sample_file_id}.txt"

    def _job_artifact_dir(self, job_id: str) -> Path:
        return self._storage_root() / "style-analysis-artifacts" / job_id

    def _log_artifact_path(self, job_id: str) -> Path:
        return self._job_artifact_dir(job_id) / "execution.log"

    def _chunk_artifact_path(self, job_id: str, chunk_index: int) -> Path:
        return self._job_artifact_dir(job_id) / "chunks" / f"{chunk_index:06d}.txt"

    def _chunk_analysis_artifact_path(self, job_id: str, chunk_index: int) -> Path:
        return self._job_artifact_dir(job_id) / "chunk-analyses" / f"{chunk_index:06d}.json"

    def _stage_artifact_path(self, job_id: str, name: str) -> Path:
        return self._job_artifact_dir(job_id) / f"{name}.md"

    def _json_artifact_path(self, job_id: str, name: str) -> Path:
        return self._job_artifact_dir(job_id) / f"{name}.json"

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
        content_stream: AsyncIterator[bytes],
    ) -> tuple[str, int, str]:
        storage_path = self._build_storage_path(sample_file_id)
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        hasher = hashlib.sha256()
        total_bytes_out = 0

        try:
            async with aiofiles.open(storage_path, "wb") as handle:
                async for chunk in content_stream:
                    hasher.update(chunk)
                    total_bytes_out += len(chunk)
                    await handle.write(chunk)
        except Exception:
            storage_path.unlink(missing_ok=True)
            raise

        if total_bytes_out == 0:
            storage_path.unlink(missing_ok=True)
            raise UnprocessableEntityError("上传的 TXT 文件为空")

        return str(storage_path), total_bytes_out, hasher.hexdigest()

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

    def chunk_analysis_artifact_exists(self, job_id: str, chunk_index: int) -> bool:
        return self._chunk_analysis_artifact_path(job_id, chunk_index).exists()

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

    async def write_stage_markdown_artifact(
        self,
        job_id: str,
        *,
        name: str,
        markdown: str,
    ) -> None:
        path = self._stage_artifact_path(job_id, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(path, "w", encoding="utf-8") as handle:
            await handle.write(markdown)

    def stage_markdown_artifact_exists(self, job_id: str, *, name: str) -> bool:
        return self._stage_artifact_path(job_id, name).exists()

    async def read_stage_markdown_artifact(self, job_id: str, *, name: str) -> str:
        path = self._stage_artifact_path(job_id, name)
        async with aiofiles.open(path, "r", encoding="utf-8") as handle:
            return await handle.read()

    async def write_json_artifact(self, job_id: str, *, name: str, payload: dict) -> None:
        path = self._json_artifact_path(job_id, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(path, "w", encoding="utf-8") as handle:
            await handle.write(json.dumps(payload, ensure_ascii=False))

    def json_artifact_exists(self, job_id: str, *, name: str) -> bool:
        return self._json_artifact_path(job_id, name).exists()

    async def read_json_artifact(self, job_id: str, *, name: str) -> dict:
        path = self._json_artifact_path(job_id, name)
        async with aiofiles.open(path, "r", encoding="utf-8") as handle:
            return json.loads(await handle.read())

    def chunk_artifacts_exist(self, job_id: str) -> bool:
        return (self._job_artifact_dir(job_id) / "chunks").exists()

    def count_chunk_artifacts(self, job_id: str) -> int:
        chunk_dir = self._job_artifact_dir(job_id) / "chunks"
        if not chunk_dir.exists():
            return 0
        return len(list(chunk_dir.glob("*.txt")))

    async def cleanup_job_artifacts(self, job_id: str) -> None:
        artifact_dir = self._job_artifact_dir(job_id)
        if artifact_dir.exists():
            await asyncio.to_thread(shutil.rmtree, artifact_dir, ignore_errors=True)

    async def job_artifacts_exist(self, job_id: str) -> bool:
        return self._job_artifact_dir(job_id).exists()

    async def append_job_log(self, job_id: str, message: str) -> None:
        from datetime import datetime, UTC
        path = self._log_artifact_path(job_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).isoformat(timespec="milliseconds")
        log_line = f"[{timestamp}] {message}\n"
        # 使用 aiofiles 追加写入
        async with aiofiles.open(path, "a", encoding="utf-8") as handle:
            await handle.write(log_line)

    async def read_job_logs(self, job_id: str) -> str:
        path = self._log_artifact_path(job_id)
        if not path.exists():
            return ""
        async with aiofiles.open(path, "r", encoding="utf-8") as handle:
            return await handle.read()

    async def read_job_logs_incremental(
        self,
        job_id: str,
        *,
        offset: int,
        max_bytes: int = 64 * 1024,
    ) -> tuple[str, int, bool]:
        path = self._log_artifact_path(job_id)
        if not path.exists():
            return "", 0, False

        safe_offset = max(offset, 0)
        file_size = path.stat().st_size
        truncated = safe_offset > file_size
        effective_offset = 0 if truncated else safe_offset

        async with aiofiles.open(path, "rb") as handle:
            await handle.seek(effective_offset)
            raw_content = await handle.read(max_bytes)
            content = raw_content.decode("utf-8")

        next_offset = min(file_size, effective_offset + len(raw_content))
        return content, next_offset, truncated
