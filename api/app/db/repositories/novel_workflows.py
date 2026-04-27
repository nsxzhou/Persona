from __future__ import annotations

from datetime import datetime

from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import NovelWorkflowRun


class NovelWorkflowRepository:
    async def list(
        self,
        session: AsyncSession,
        *,
        user_id: str | None = None,
        offset: int,
        limit: int,
    ) -> list[NovelWorkflowRun]:
        stmt = (
            select(NovelWorkflowRun)
            .options(
                joinedload(NovelWorkflowRun.provider),
                joinedload(NovelWorkflowRun.project),
                joinedload(NovelWorkflowRun.chapter),
            )
            .order_by(NovelWorkflowRun.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if user_id is not None:
            stmt = stmt.where(NovelWorkflowRun.user_id == user_id)
        result = await session.stream_scalars(stmt)
        return [run async for run in result]

    async def get_by_id(
        self,
        session: AsyncSession,
        run_id: str,
        *,
        user_id: str | None = None,
    ) -> NovelWorkflowRun | None:
        stmt = (
            select(NovelWorkflowRun)
            .options(
                joinedload(NovelWorkflowRun.provider),
                joinedload(NovelWorkflowRun.project),
                joinedload(NovelWorkflowRun.chapter),
            )
            .where(NovelWorkflowRun.id == run_id)
        )
        if user_id is not None:
            stmt = stmt.where(NovelWorkflowRun.user_id == user_id)
        return await session.scalar(stmt)

    async def create_run(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        project_id: str | None,
        chapter_id: str | None,
        provider_id: str | None,
        intent_type: str,
        model_name: str | None,
        request_payload: dict,
        pending_status: str,
    ) -> NovelWorkflowRun:
        run = NovelWorkflowRun(
            user_id=user_id,
            project_id=project_id,
            chapter_id=chapter_id,
            provider_id=provider_id,
            intent_type=intent_type,
            model_name=model_name,
            request_payload=request_payload,
            latest_artifacts_payload=[],
            warnings_payload=[],
            decision_payload=None,
            status=pending_status,
            stage=None,
            checkpoint_kind=None,
            error_message=None,
            locked_by=None,
            locked_at=None,
            last_heartbeat_at=None,
            pause_requested_at=None,
            paused_at=None,
            attempt_count=0,
        )
        session.add(run)
        await session.flush()
        return run

    async def claim_pending_run(
        self,
        session: AsyncSession,
        *,
        worker_id: str,
        max_attempts: int,
        preparing_stage: str,
        running_status: str,
        pending_status: str,
        now: datetime,
    ) -> str | None:
        candidate_subquery = (
            select(NovelWorkflowRun.id)
            .where(
                NovelWorkflowRun.status == pending_status,
                NovelWorkflowRun.attempt_count < max_attempts,
            )
            .order_by(NovelWorkflowRun.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
            .scalar_subquery()
        )

        result = await session.execute(
            update(NovelWorkflowRun)
            .where(
                NovelWorkflowRun.id == candidate_subquery,
                NovelWorkflowRun.status == pending_status,
                NovelWorkflowRun.attempt_count < max_attempts,
            )
            .values(
                status=running_status,
                stage=preparing_stage,
                error_message=None,
                started_at=now,
                completed_at=None,
                locked_by=worker_id,
                locked_at=now,
                last_heartbeat_at=now,
                attempt_count=NovelWorkflowRun.attempt_count + 1,
            )
            .returning(NovelWorkflowRun.id)
        )
        return result.scalar_one_or_none()

    async def heartbeat(
        self,
        session: AsyncSession,
        run_id: str,
        *,
        running_status: str,
        stage: str | None,
        checkpoint_kind: str | None,
        now: datetime,
    ) -> datetime | None:
        result = await session.execute(
            update(NovelWorkflowRun)
            .where(
                NovelWorkflowRun.id == run_id,
                NovelWorkflowRun.status == running_status,
            )
            .values(
                stage=stage,
                checkpoint_kind=checkpoint_kind,
                last_heartbeat_at=now,
            )
            .returning(NovelWorkflowRun.pause_requested_at)
        )
        return result.scalar_one_or_none()

    async def request_pause(
        self,
        session: AsyncSession,
        run_id: str,
        *,
        running_status: str,
        now: datetime,
    ) -> bool:
        result = await session.execute(
            update(NovelWorkflowRun)
            .where(
                NovelWorkflowRun.id == run_id,
                NovelWorkflowRun.status == running_status,
                NovelWorkflowRun.pause_requested_at.is_(None),
            )
            .values(pause_requested_at=now)
        )
        return bool(result.rowcount)

    async def mark_paused(
        self,
        session: AsyncSession,
        run_id: str,
        *,
        paused_status: str,
        now: datetime,
        stage: str | None,
        checkpoint_kind: str | None,
    ) -> None:
        await session.execute(
            update(NovelWorkflowRun)
            .where(NovelWorkflowRun.id == run_id)
            .values(
                status=paused_status,
                paused_at=now,
                pause_requested_at=None,
                stage=stage,
                checkpoint_kind=checkpoint_kind,
                error_message=None,
                locked_by=None,
                locked_at=None,
                last_heartbeat_at=None,
                attempt_count=case(
                    (NovelWorkflowRun.attempt_count > 0, NovelWorkflowRun.attempt_count - 1),
                    else_=0,
                ),
            )
        )

    async def reconcile_stale_run(
        self,
        session: AsyncSession,
        run_id: str,
        *,
        cutoff: datetime,
        max_attempts: int,
        running_status: str,
        paused_status: str,
        failed_status: str,
        pending_status: str,
        now: datetime,
    ) -> bool:
        stale_condition = (
            (NovelWorkflowRun.id == run_id)
            & (NovelWorkflowRun.status == running_status)
            & (
                func.coalesce(
                    NovelWorkflowRun.last_heartbeat_at,
                    NovelWorkflowRun.started_at,
                )
                < cutoff
            )
        )

        affected_rows = 0
        result = await session.execute(
            update(NovelWorkflowRun)
            .where(stale_condition, NovelWorkflowRun.pause_requested_at.is_not(None))
            .values(
                status=paused_status,
                paused_at=now,
                pause_requested_at=None,
                locked_by=None,
                locked_at=None,
                last_heartbeat_at=None,
                attempt_count=case(
                    (NovelWorkflowRun.attempt_count > 0, NovelWorkflowRun.attempt_count - 1),
                    else_=0,
                ),
            )
        )
        affected_rows += result.rowcount or 0

        result = await session.execute(
            update(NovelWorkflowRun)
            .where(
                stale_condition,
                NovelWorkflowRun.pause_requested_at.is_(None),
                NovelWorkflowRun.attempt_count >= max_attempts,
            )
            .values(
                status=failed_status,
                error_message="工作流重试次数已用尽，请重新提交",
                completed_at=now,
                stage=None,
                checkpoint_kind=None,
                locked_by=None,
                locked_at=None,
                last_heartbeat_at=None,
            )
        )
        affected_rows += result.rowcount or 0

        result = await session.execute(
            update(NovelWorkflowRun)
            .where(
                stale_condition,
                NovelWorkflowRun.pause_requested_at.is_(None),
                NovelWorkflowRun.attempt_count < max_attempts,
            )
            .values(
                status=pending_status,
                stage=None,
                checkpoint_kind=None,
                error_message=None,
                locked_by=None,
                locked_at=None,
                last_heartbeat_at=None,
            )
        )
        affected_rows += result.rowcount or 0
        return affected_rows > 0

    async def recover_stale_runs(
        self,
        session: AsyncSession,
        *,
        cutoff: datetime,
        max_attempts: int,
        running_status: str,
        paused_status: str,
        failed_status: str,
        pending_status: str,
        now: datetime,
    ) -> None:
        stale_ids = await session.scalars(
            select(NovelWorkflowRun.id).where(
                NovelWorkflowRun.status == running_status,
                func.coalesce(
                    NovelWorkflowRun.last_heartbeat_at,
                    NovelWorkflowRun.started_at,
                )
                < cutoff,
            )
        )
        for run_id in list(stale_ids):
            await self.reconcile_stale_run(
                session,
                run_id,
                cutoff=cutoff,
                max_attempts=max_attempts,
                running_status=running_status,
                paused_status=paused_status,
                failed_status=failed_status,
                pending_status=pending_status,
                now=now,
            )

    async def flush(self, session: AsyncSession) -> None:
        await session.flush()
