from __future__ import annotations

import asyncio
import shutil
from datetime import UTC, datetime
from pathlib import Path

import aiofiles

from app.core.config import get_settings


class NovelWorkflowStorageService:
    def _storage_root(self) -> Path:
        return Path(get_settings().storage_dir).expanduser()

    def _artifact_dir(self, run_id: str) -> Path:
        return self._storage_root() / "novel-workflow-artifacts" / run_id

    def _artifact_path(self, run_id: str, name: str) -> Path:
        return self._artifact_dir(run_id) / f"{name}.md"

    def _log_path(self, run_id: str) -> Path:
        return self._artifact_dir(run_id) / "execution.log"

    async def write_stage_markdown_artifact(
        self,
        run_id: str,
        *,
        name: str,
        markdown: str,
    ) -> None:
        path = self._artifact_path(run_id, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(path, "w", encoding="utf-8") as handle:
            await handle.write(markdown)

    def stage_markdown_artifact_exists(self, run_id: str, *, name: str) -> bool:
        return self._artifact_path(run_id, name).exists()

    async def read_stage_markdown_artifact(self, run_id: str, *, name: str) -> str:
        path = self._artifact_path(run_id, name)
        async with aiofiles.open(path, "r", encoding="utf-8") as handle:
            return await handle.read()

    async def append_job_log(self, run_id: str, message: str) -> None:
        path = self._log_path(run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).isoformat(timespec="milliseconds")
        async with aiofiles.open(path, "a", encoding="utf-8") as handle:
            await handle.write(f"[{timestamp}] {message}\n")

    async def read_job_logs_incremental(
        self,
        run_id: str,
        *,
        offset: int,
        max_bytes: int = 64 * 1024,
    ) -> tuple[str, int, bool]:
        path = self._log_path(run_id)
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

    async def cleanup_run_artifacts(self, run_id: str) -> None:
        artifact_dir = self._artifact_dir(run_id)
        if artifact_dir.exists():
            await asyncio.to_thread(shutil.rmtree, artifact_dir, ignore_errors=True)
