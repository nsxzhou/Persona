from __future__ import annotations

from datetime import datetime

from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer, joinedload

from app.db.models import StyleAnalysisJob, StyleProfile, StyleSampleFile


class StyleAnalysisJobRepository:
    async def list(
        self,
        session: AsyncSession,
        *,
        user_id: str | None = None,
        offset: int,
        limit: int,
        include_payloads: bool = False,
    ) -> list[StyleAnalysisJob]:
        stmt = (
            select(StyleAnalysisJob)
            .options(
                joinedload(StyleAnalysisJob.provider),
                joinedload(StyleAnalysisJob.sample_file),
                joinedload(StyleAnalysisJob.style_profile).load_only(StyleProfile.id),
            )
            .order_by(StyleAnalysisJob.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if user_id is not None:
            stmt = stmt.where(StyleAnalysisJob.user_id == user_id)
        if not include_payloads:
            stmt = stmt.options(
                defer(StyleAnalysisJob.analysis_report_payload),
                defer(StyleAnalysisJob.voice_profile_payload),
            )
        result = await session.stream_scalars(stmt)
        return [job async for job in result]

    async def get_by_id(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str | None = None,
        include_payloads: bool = True,
        include_style_profile_payloads: bool = True,
    ) -> StyleAnalysisJob | None:
        style_profile_option = joinedload(StyleAnalysisJob.style_profile)
        if not include_style_profile_payloads:
            style_profile_option = style_profile_option.load_only(StyleProfile.id)
        stmt = select(StyleAnalysisJob).options(
            joinedload(StyleAnalysisJob.provider),
            joinedload(StyleAnalysisJob.sample_file),
            style_profile_option,
        )
        if not include_payloads:
            stmt = stmt.options(
                defer(StyleAnalysisJob.analysis_report_payload),
                defer(StyleAnalysisJob.voice_profile_payload),
            )
        stmt = stmt.where(StyleAnalysisJob.id == job_id)
        if user_id is not None:
            stmt = stmt.where(StyleAnalysisJob.user_id == user_id)
        return await session.scalar(stmt)

    async def get_status_and_payload(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str | None = None,
        payload_column,
    ):
        stmt = select(StyleAnalysisJob.status, payload_column).where(
            StyleAnalysisJob.id == job_id
        )
        if user_id is not None:
            stmt = stmt.where(StyleAnalysisJob.user_id == user_id)
        row = await session.execute(stmt)
        return row.one_or_none()

    async def get_for_delete(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str | None = None,
    ) -> StyleAnalysisJob | None:
        stmt = (
            select(StyleAnalysisJob)
            .options(
                joinedload(StyleAnalysisJob.sample_file),
                joinedload(StyleAnalysisJob.style_profile).selectinload(
                    StyleProfile.projects
                ),
            )
            .where(StyleAnalysisJob.id == job_id)
        )
        if user_id is not None:
            stmt = stmt.where(StyleAnalysisJob.user_id == user_id)
        return await session.scalar(stmt)

    async def claim_pending_job(
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
            select(StyleAnalysisJob.id)
            .where(
                StyleAnalysisJob.status == pending_status,
                StyleAnalysisJob.attempt_count < max_attempts,
            )
            .order_by(StyleAnalysisJob.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
            .scalar_subquery()
        )

        result = await session.execute(
            update(StyleAnalysisJob)
            .where(
                StyleAnalysisJob.id == candidate_subquery,
                StyleAnalysisJob.status == pending_status,
                StyleAnalysisJob.attempt_count < max_attempts,
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
                attempt_count=StyleAnalysisJob.attempt_count + 1,
            )
            .returning(StyleAnalysisJob.id)
        )
        return result.scalar_one_or_none()

    async def heartbeat(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        running_status: str,
        stage: str | None,
        now: datetime,
    ) -> datetime | None:
        result = await session.execute(
            update(StyleAnalysisJob)
            .where(
                StyleAnalysisJob.id == job_id, StyleAnalysisJob.status == running_status
            )
            .values(stage=stage, last_heartbeat_at=now)
            .returning(StyleAnalysisJob.pause_requested_at)
        )
        return result.scalar_one_or_none()

    async def request_pause(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        running_status: str,
        now: datetime,
    ) -> bool:
        result = await session.execute(
            update(StyleAnalysisJob)
            .where(
                StyleAnalysisJob.id == job_id,
                StyleAnalysisJob.status == running_status,
                StyleAnalysisJob.pause_requested_at.is_(None),
            )
            .values(pause_requested_at=now)
        )
        return bool(result.rowcount)

    async def mark_paused(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        paused_status: str,
        now: datetime,
        stage: str | None,
    ) -> None:
        await session.execute(
            update(StyleAnalysisJob)
            .where(StyleAnalysisJob.id == job_id)
            .values(
                status=paused_status,
                paused_at=now,
                pause_requested_at=None,
                stage=stage,
                error_message=None,
                locked_by=None,
                locked_at=None,
                last_heartbeat_at=None,
                attempt_count=case(
                    (StyleAnalysisJob.attempt_count > 0, StyleAnalysisJob.attempt_count - 1),
                    else_=0,
                ),
            )
        )

    async def _apply_stale_recovery(
        self,
        session: AsyncSession,
        stale_condition,
        max_attempts: int,
        paused_status: str,
        failed_status: str,
        pending_status: str,
        now: datetime,
    ) -> int:
        pause_condition = stale_condition & (StyleAnalysisJob.pause_requested_at.is_not(None))
        affected_rows = 0

        result = await session.execute(
            update(StyleAnalysisJob)
            .where(pause_condition)
            .values(
                status=paused_status,
                paused_at=now,
                pause_requested_at=None,
                locked_by=None,
                locked_at=None,
                last_heartbeat_at=None,
                attempt_count=case(
                    (StyleAnalysisJob.attempt_count > 0, StyleAnalysisJob.attempt_count - 1),
                    else_=0,
                ),
            )
        )
        affected_rows += result.rowcount or 0

        result = await session.execute(
            update(StyleAnalysisJob)
            .where(
                stale_condition,
                StyleAnalysisJob.pause_requested_at.is_(None),
                StyleAnalysisJob.attempt_count >= max_attempts,
            )
            .values(
                status=failed_status,
                error_message="分析任务重试次数已用尽，请重新提交",
                completed_at=now,
                stage=None,
                locked_by=None,
                locked_at=None,
                last_heartbeat_at=None,
            )
        )
        affected_rows += result.rowcount or 0

        result = await session.execute(
            update(StyleAnalysisJob)
            .where(
                stale_condition,
                StyleAnalysisJob.pause_requested_at.is_(None),
                StyleAnalysisJob.attempt_count < max_attempts,
            )
            .values(
                status=pending_status,
                stage=None,
                error_message=None,
                locked_by=None,
                locked_at=None,
                last_heartbeat_at=None,
            )
        )
        affected_rows += result.rowcount or 0
        return affected_rows

    async def recover_stale_jobs(
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
        stale_condition = (StyleAnalysisJob.status == running_status) & (
            func.coalesce(
                StyleAnalysisJob.last_heartbeat_at,
                StyleAnalysisJob.started_at,
            )
            < cutoff
        )
        await self._apply_stale_recovery(
            session=session,
            stale_condition=stale_condition,
            max_attempts=max_attempts,
            paused_status=paused_status,
            failed_status=failed_status,
            pending_status=pending_status,
            now=now,
        )

    async def reconcile_stale_job(
        self,
        session: AsyncSession,
        job_id: str,
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
            (StyleAnalysisJob.id == job_id)
            & (StyleAnalysisJob.status == running_status)
            & (
                func.coalesce(
                    StyleAnalysisJob.last_heartbeat_at,
                    StyleAnalysisJob.started_at,
                )
                < cutoff
            )
        )
        affected_rows = await self._apply_stale_recovery(
            session=session,
            stale_condition=stale_condition,
            max_attempts=max_attempts,
            paused_status=paused_status,
            failed_status=failed_status,
            pending_status=pending_status,
            now=now,
        )
        return affected_rows > 0

    async def create_sample_file(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        original_filename: str,
        content_type: str | None,
    ) -> StyleSampleFile:
        sample_file = StyleSampleFile(
            user_id=user_id,
            original_filename=original_filename,
            content_type=content_type,
            storage_path="",
            byte_size=0,
            character_count=None,
            checksum_sha256="",
        )
        session.add(sample_file)
        await session.flush()
        return sample_file

    async def create_job(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        style_name: str,
        provider_id: str,
        model_name: str,
        sample_file_id: str,
        pending_status: str,
    ) -> StyleAnalysisJob:
        job = StyleAnalysisJob(
            user_id=user_id,
            style_name=style_name,
            provider_id=provider_id,
            model_name=model_name,
            sample_file_id=sample_file_id,
            status=pending_status,
            stage=None,
            error_message=None,
            analysis_meta_payload=None,
            analysis_report_payload=None,
            voice_profile_payload=None,
            locked_by=None,
            locked_at=None,
            last_heartbeat_at=None,
            attempt_count=0,
        )
        session.add(job)
        await session.flush()
        return job

    async def flush(self, session: AsyncSession) -> None:
        await session.flush()

    async def delete_job_graph(
        self,
        session: AsyncSession,
        job: StyleAnalysisJob,
    ) -> None:
        if job.style_profile is not None:
            await session.delete(job.style_profile)
        await session.delete(job)
        if job.sample_file is not None:
            await session.delete(job.sample_file)
