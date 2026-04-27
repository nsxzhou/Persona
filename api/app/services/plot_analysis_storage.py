from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from pathlib import Path

import aiofiles

from app.services.base_analysis_storage import BaseAnalysisStorageService
from app.services.plot_analysis_chunking import PlotChunkContext
from app.services.plot_analysis_text import PlotChunkManifestEntry


class PlotAnalysisStorageService(BaseAnalysisStorageService):
    @property
    def sample_dir_name(self) -> str:
        return "plot-samples"

    @property
    def artifact_dir_name(self) -> str:
        return "plot-analysis-artifacts"

    def _sketch_artifact_path(self, job_id: str, chunk_index: int) -> Path:
        return self._job_artifact_dir(job_id) / "sketches" / f"{chunk_index:06d}.json"

    async def write_chunk_manifest(
        self,
        job_id: str,
        manifest: list[PlotChunkManifestEntry],
    ) -> None:
        await self.write_json_artifact(job_id, name="chunk-manifest", payload={"chunks": manifest})

    async def read_chunk_manifest(self, job_id: str) -> list[PlotChunkManifestEntry]:
        if not self.json_artifact_exists(job_id, name="chunk-manifest"):
            return []
        payload = await self.read_json_artifact(job_id, name="chunk-manifest")
        chunks = payload.get("chunks")
        if not isinstance(chunks, list):
            return []
        return [item for item in chunks if isinstance(item, dict)]

    async def read_chunk_with_overlap_context(
        self,
        job_id: str,
        chunk_index: int,
    ) -> PlotChunkContext:
        primary_text = await self.read_chunk_artifact(job_id, chunk_index)
        manifest = await self.read_chunk_manifest(job_id)
        if not manifest or chunk_index >= len(manifest):
            return PlotChunkContext(primary_text=primary_text)
        entry = manifest[chunk_index]
        overlap_before = ""
        overlap_after = ""
        overlap_before_chars = int(entry.get("overlap_before_chars", 0) or 0)
        overlap_after_chars = int(entry.get("overlap_after_chars", 0) or 0)
        if overlap_before_chars > 0 and chunk_index > 0:
            previous_text = await self.read_chunk_artifact(job_id, chunk_index - 1)
            overlap_before = previous_text[-overlap_before_chars:]
        if overlap_after_chars > 0 and chunk_index + 1 < len(manifest):
            next_text = await self.read_chunk_artifact(job_id, chunk_index + 1)
            overlap_after = next_text[:overlap_after_chars]
        return PlotChunkContext(
            primary_text=primary_text,
            overlap_before=overlap_before,
            overlap_after=overlap_after,
        )

    async def write_sketch_artifact(
        self,
        job_id: str,
        chunk_index: int,
        payload: dict,
    ) -> None:
        final_path = self._sketch_artifact_path(job_id, chunk_index)
        final_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = final_path.with_suffix(final_path.suffix + ".tmp")
        try:
            async with aiofiles.open(tmp_path, "w", encoding="utf-8") as handle:
                await handle.write(json.dumps(payload, ensure_ascii=False))
            os.replace(tmp_path, final_path)
        except BaseException:
            tmp_path.unlink(missing_ok=True)
            raise

    def sketch_artifact_exists(self, job_id: str, chunk_index: int) -> bool:
        return self._sketch_artifact_path(job_id, chunk_index).exists()

    async def read_sketch_batches(
        self,
        job_id: str,
        *,
        batch_size: int,
    ) -> AsyncIterator[list[dict]]:
        sketch_dir = self._job_artifact_dir(job_id) / "sketches"
        if not sketch_dir.exists():
            return

        paths = sorted(sketch_dir.glob("*.json"))
        batch: list[dict] = []
        for path in paths:
            async with aiofiles.open(path, "r", encoding="utf-8") as handle:
                batch.append(json.loads(await handle.read()))
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

    async def read_all_sketches(self, job_id: str) -> list[dict]:
        sketch_dir = self._job_artifact_dir(job_id) / "sketches"
        if not sketch_dir.exists():
            return []

        paths = sorted(sketch_dir.glob("*.json"))
        sketches: list[dict] = []
        for path in paths:
            async with aiofiles.open(path, "r", encoding="utf-8") as handle:
                sketches.append(json.loads(await handle.read()))
        sketches.sort(key=lambda item: item["chunk_index"])
        return sketches

    def count_sketch_artifacts(self, job_id: str) -> int:
        sketch_dir = self._job_artifact_dir(job_id) / "sketches"
        if not sketch_dir.exists():
            return 0
        return len(list(sketch_dir.glob("*.json")))
