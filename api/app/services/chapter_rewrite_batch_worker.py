from __future__ import annotations

import asyncio
import logging
import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.services.chapter_rewrite_batches import ChapterRewriteBatchService

logger = logging.getLogger(__name__)


class ChapterRewriteBatchWorkerService:
    def __init__(self) -> None:
        self.batch_service = ChapterRewriteBatchService()
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
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be greater than 0")
        max_poll_interval_seconds = max_poll_interval_seconds or poll_interval_seconds
        if max_poll_interval_seconds < poll_interval_seconds:
            max_poll_interval_seconds = poll_interval_seconds
        settings = get_settings()
        last_stale_check = 0.0
        stale_check_interval = max(
            5.0,
            float(settings.style_analysis_stale_timeout_seconds) / 3.0,
        )
        current_interval = poll_interval_seconds
        while True:
            now = time.monotonic()
            if now - last_stale_check >= stale_check_interval:
                await self.fail_stale_running_batches(
                    session_factory,
                    stale_after_seconds=settings.style_analysis_stale_timeout_seconds,
                )
                last_stale_check = now
            processed = await self.process_next_pending(session_factory)
            if processed:
                current_interval = poll_interval_seconds
                continue
            await asyncio.sleep(current_interval)
            current_interval = min(max_poll_interval_seconds, current_interval * 2)
