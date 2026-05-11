from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.db.models import ChapterRewriteBatch, ChapterRewriteBatchItem


class ChapterRewriteBatchRepository:
    async def create(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        project_id: str,
        instruction: str,
        chapter_ids: list[str],
        pending_status: str,
        item_waiting_status: str,
    ) -> ChapterRewriteBatch:
        batch = ChapterRewriteBatch(
            user_id=user_id,
            project_id=project_id,
            instruction=instruction,
            status=pending_status,
            stage=None,
            error_message=None,
            total_count=len(chapter_ids),
            generated_count=0,
            failed_count=0,
            applied_count=0,
        )
        batch.items = [
            ChapterRewriteBatchItem(
                chapter_id=chapter_id,
                position=index,
                status=item_waiting_status,
                stage=None,
                error_message=None,
            )
            for index, chapter_id in enumerate(chapter_ids)
        ]
        session.add(batch)
        await session.flush()
        return batch

    async def list(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        project_id: str | None,
        offset: int,
        limit: int,
    ) -> list[ChapterRewriteBatch]:
        stmt = (
            select(ChapterRewriteBatch)
            .options(
                selectinload(ChapterRewriteBatch.items).joinedload(
                    ChapterRewriteBatchItem.chapter
                )
            )
            .where(ChapterRewriteBatch.user_id == user_id)
            .order_by(ChapterRewriteBatch.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if project_id is not None:
            stmt = stmt.where(ChapterRewriteBatch.project_id == project_id)
        result = await session.stream_scalars(stmt)
        return [batch async for batch in result]

    async def get_by_id(
        self,
        session: AsyncSession,
        batch_id: str,
        *,
        user_id: str | None = None,
    ) -> ChapterRewriteBatch | None:
        stmt = (
            select(ChapterRewriteBatch)
            .options(
                selectinload(ChapterRewriteBatch.items)
                .joinedload(ChapterRewriteBatchItem.chapter),
            )
            .where(ChapterRewriteBatch.id == batch_id)
        )
        if user_id is not None:
            stmt = stmt.where(ChapterRewriteBatch.user_id == user_id)
        return await session.scalar(stmt)

    async def get_item_by_id(
        self,
        session: AsyncSession,
        batch_id: str,
        item_id: str,
        *,
        user_id: str | None = None,
    ) -> ChapterRewriteBatchItem | None:
        stmt = (
            select(ChapterRewriteBatchItem)
            .join(ChapterRewriteBatch)
            .options(
                joinedload(ChapterRewriteBatchItem.batch),
                joinedload(ChapterRewriteBatchItem.chapter),
                joinedload(ChapterRewriteBatchItem.child_run),
            )
            .where(
                ChapterRewriteBatchItem.batch_id == batch_id,
                ChapterRewriteBatchItem.id == item_id,
            )
        )
        if user_id is not None:
            stmt = stmt.where(ChapterRewriteBatch.user_id == user_id)
        return await session.scalar(stmt)

    async def claim_pending_batch(
        self,
        session: AsyncSession,
        *,
        worker_id: str,
        pending_status: str,
        running_status: str,
        now: datetime,
    ) -> str | None:
        candidate_subquery = (
            select(ChapterRewriteBatch.id)
            .where(ChapterRewriteBatch.status == pending_status)
            .order_by(ChapterRewriteBatch.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
            .scalar_subquery()
        )
        result = await session.execute(
            update(ChapterRewriteBatch)
            .where(
                ChapterRewriteBatch.id == candidate_subquery,
                ChapterRewriteBatch.status == pending_status,
            )
            .values(
                status=running_status,
                stage="preparing",
                error_message=None,
                started_at=now,
                completed_at=None,
                locked_by=worker_id,
                locked_at=now,
                last_heartbeat_at=now,
            )
            .returning(ChapterRewriteBatch.id)
        )
        return result.scalar_one_or_none()

    async def recover_stale_batches(
        self,
        session: AsyncSession,
        *,
        cutoff: datetime,
        running_status: str,
        failed_status: str,
        now: datetime,
    ) -> None:
        await session.execute(
            update(ChapterRewriteBatch)
            .where(
                ChapterRewriteBatch.status == running_status,
                func.coalesce(
                    ChapterRewriteBatch.last_heartbeat_at,
                    ChapterRewriteBatch.started_at,
                )
                < cutoff,
            )
            .values(
                status=failed_status,
                stage=None,
                error_message="章节改写批次运行超时，请重新提交",
                completed_at=now,
                locked_by=None,
                locked_at=None,
                last_heartbeat_at=None,
            )
        )

    async def flush(self, session: AsyncSession) -> None:
        await session.flush()
