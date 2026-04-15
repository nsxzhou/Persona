from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import StyleAnalysisJob
from app.db.repositories.style_analysis_jobs import StyleAnalysisJobRepository
from app.services.style_analysis_job_file_lifecycle import (
    StyleAnalysisJobFileLifecycleService,
)

logger = logging.getLogger(__name__)


class StyleAnalysisJobCleanupService:
    def __init__(
        self,
        repository: StyleAnalysisJobRepository | None = None,
        file_lifecycle: StyleAnalysisJobFileLifecycleService | None = None,
    ) -> None:
        self.repository = repository or StyleAnalysisJobRepository()
        self.file_lifecycle = file_lifecycle or StyleAnalysisJobFileLifecycleService()

    async def delete_job_and_artifacts(
        self,
        session: AsyncSession,
        job: StyleAnalysisJob,
        job_id: str,
    ) -> None:
        sample_storage_path = job.sample_file.storage_path
        await self.repository.delete_job_graph(session, job)
        await self.file_lifecycle.cleanup_after_job_delete(
            sample_storage_path=sample_storage_path,
            job_id=job_id,
        )

        try:
            from app.services.style_analysis_checkpointer import (
                StyleAnalysisCheckpointerFactory,
            )

            checkpointer_factory = StyleAnalysisCheckpointerFactory()
            await checkpointer_factory.delete_thread(job_id)
            await checkpointer_factory.aclose()
        except Exception:
            logger.warning("Failed to clean up checkpointer thread for job %s", job_id, exc_info=True)
