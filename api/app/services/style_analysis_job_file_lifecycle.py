from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile

from app.services.style_analysis_storage import StyleAnalysisStorageService


class StyleAnalysisJobFileLifecycleService:
    def __init__(self, storage_service: StyleAnalysisStorageService | None = None) -> None:
        self.storage_service = storage_service or StyleAnalysisStorageService()

    async def persist_sample_upload(
        self,
        sample_file_id: str,
        upload_file: UploadFile,
    ) -> tuple[str, int, str]:
        return await self.storage_service.save_file(sample_file_id, upload_file)

    async def cleanup_after_job_delete(
        self,
        *,
        sample_storage_path: str | None,
        job_id: str,
    ) -> None:
        if sample_storage_path:
            try:
                Path(sample_storage_path).unlink(missing_ok=True)
            except OSError:
                pass
        await self.storage_service.cleanup_job_artifacts(job_id)
