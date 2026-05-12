from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.services.chapter_rewrite_batches import ChapterRewriteBatchService
from app.services.analysis_worker_lifecycle import run_analysis_worker_poll_loop

logger = logging.getLogger(__name__)


class ChapterRewriteBatchWorkerService:
    def __init__(self, batch_service: ChapterRewriteBatchService | None = None) -> None:
        self.batch_service = batch_service or ChapterRewriteBatchService()
        self._worker_id = f"chapter-batch-worker-{uuid.uuid4()}"

    async def aclose(self) -> None:
        return None

    async def process_next_pending(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> bool:
        async with session_factory.begin() as session:
            batch_id = await self.batch_service.claim_next_pending_batch(
                session,
                worker_id=self._worker_id,
            )
        if batch_id is None:
            return False
        try:
            await self.batch_service.process_claimed_batch(session_factory, batch_id)
        except Exception:
            logger.exception("chapter rewrite batch failed", extra={"batch_id": batch_id})
            raise
        return True

    async def fail_stale_running_batches(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        stale_after_seconds: int,
    ) -> None:
        async with session_factory.begin() as session:
            await self.batch_service.recover_stale_batches(
                session,
                stale_after_seconds=stale_after_seconds,
            )

    async def run_worker(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        poll_interval_seconds: float,
        max_poll_interval_seconds: float | None = None,
    ) -> None:
        settings = get_settings()
        await run_analysis_worker_poll_loop(
            poll_interval_seconds=poll_interval_seconds,
            max_poll_interval_seconds=max_poll_interval_seconds,
            stale_timeout_seconds=settings.novel_workflow_stale_timeout_seconds,
            fail_stale_running_jobs=lambda stale_after_seconds: self.fail_stale_running_batches(
                session_factory,
                stale_after_seconds=stale_after_seconds,
            ),
            process_next_pending=lambda: self.process_next_pending(session_factory),
        )
