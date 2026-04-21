from __future__ import annotations

from datetime import datetime

from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer, joinedload

from app.db.models import PlotAnalysisJob, PlotProfile, PlotSampleFile


class PlotAnalysisJobRepository:
    async def list(
        self,
        session: AsyncSession,
        *,
        user_id: str | None = None,
        offset: int,
        limit: int,
        include_payloads: bool = False,
    ) -> list[PlotAnalysisJob]:
        stmt = (
            select(PlotAnalysisJob)
            .options(
                joinedload(PlotAnalysisJob.provider),
                joinedload(PlotAnalysisJob.sample_file),
                joinedload(PlotAnalysisJob.plot_profile).load_only(PlotProfile.id),
            )
            .order_by(PlotAnalysisJob.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if user_id is not None:
            stmt = stmt.where(PlotAnalysisJob.user_id == user_id)
        if not include_payloads:
            stmt = stmt.options(
                defer(PlotAnalysisJob.analysis_report_payload),
                defer(PlotAnalysisJob.plot_summary_payload),
                defer(PlotAnalysisJob.prompt_pack_payload),
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
        include_plot_profile_payloads: bool = True,
    ) -> PlotAnalysisJob | None:
        plot_profile_option = joinedload(PlotAnalysisJob.plot_profile)
        if not include_plot_profile_payloads:
            plot_profile_option = plot_profile_option.load_only(PlotProfile.id)
        stmt = select(PlotAnalysisJob).options(
            joinedload(PlotAnalysisJob.provider),
            joinedload(PlotAnalysisJob.sample_file),
            plot_profile_option,
        )
        if not include_payloads:
            stmt = stmt.options(
                defer(PlotAnalysisJob.analysis_report_payload),
                defer(PlotAnalysisJob.plot_summary_payload),
                defer(PlotAnalysisJob.prompt_pack_payload),
            )
        stmt = stmt.where(PlotAnalysisJob.id == job_id)
        if user_id is not None:
            stmt = stmt.where(PlotAnalysisJob.user_id == user_id)
        return await session.scalar(stmt)

    async def get_status_and_payload(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str | None = None,
        payload_column=None,
    ):
        stmt = select(PlotAnalysisJob.status, payload_column).where(
            PlotAnalysisJob.id == job_id
        )
        if user_id is not None:
            stmt = stmt.where(PlotAnalysisJob.user_id == user_id)
        row = await session.execute(stmt)
        return row.one_or_none()

    async def get_for_delete(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str | None = None,
    ) -> PlotAnalysisJob | None:
        stmt = (
            select(PlotAnalysisJob)
            .options(
                joinedload(PlotAnalysisJob.sample_file),
                joinedload(PlotAnalysisJob.plot_profile).selectinload(
                    PlotProfile.projects
                ),
            )
            .where(PlotAnalysisJob.id == job_id)
        )
        if user_id is not None:
            stmt = stmt.where(PlotAnalysisJob.user_id == user_id)
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
            select(PlotAnalysisJob.id)
            .where(
                PlotAnalysisJob.status == pending_status,
                PlotAnalysisJob.attempt_count < max_attempts,
            )
            .order_by(PlotAnalysisJob.created_at.asc())
            .limit(1)
            .scalar_subquery()
        )

        result = await session.execute(
            update(PlotAnalysisJob)
            .where(
                PlotAnalysisJob.id == candidate_subquery,
                PlotAnalysisJob.status == pending_status,
                PlotAnalysisJob.attempt_count < max_attempts,
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
                attempt_count=PlotAnalysisJob.attempt_count + 1,
            )
            .returning(PlotAnalysisJob.id)
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
            update(PlotAnalysisJob)
            .where(
                PlotAnalysisJob.id == job_id, PlotAnalysisJob.status == running_status
            )
            .values(stage=stage, last_heartbeat_at=now)
            .returning(PlotAnalysisJob.pause_requested_at)
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
            update(PlotAnalysisJob)
            .where(
                PlotAnalysisJob.id == job_id,
                PlotAnalysisJob.status == running_status,
                PlotAnalysisJob.pause_requested_at.is_(None),
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
            update(PlotAnalysisJob)
            .where(PlotAnalysisJob.id == job_id)
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
                    (PlotAnalysisJob.attempt_count > 0, PlotAnalysisJob.attempt_count - 1),
                    else_=0,
                ),
            )
        )

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
        stale_condition = (PlotAnalysisJob.status == running_status) & (
            func.coalesce(
                PlotAnalysisJob.last_heartbeat_at,
                PlotAnalysisJob.started_at,
            )
            < cutoff
        )
        pause_condition = stale_condition & (PlotAnalysisJob.pause_requested_at.is_not(None))

        await session.execute(
            update(PlotAnalysisJob)
            .where(pause_condition)
            .values(
                status=paused_status,
                paused_at=now,
                pause_requested_at=None,
                locked_by=None,
                locked_at=None,
                last_heartbeat_at=None,
                attempt_count=case(
                    (PlotAnalysisJob.attempt_count > 0, PlotAnalysisJob.attempt_count - 1),
                    else_=0,
                ),
            )
        )
        await session.execute(
            update(PlotAnalysisJob)
            .where(
                stale_condition,
                PlotAnalysisJob.pause_requested_at.is_(None),
            )
            .values(
                status=case(
                    (PlotAnalysisJob.attempt_count >= max_attempts, failed_status),
                    else_=pending_status,
                ),
                stage=None,
                error_message=None,
                started_at=None,
                completed_at=case(
                    (PlotAnalysisJob.attempt_count >= max_attempts, now),
                    else_=None,
                ),
                locked_by=None,
                locked_at=None,
                last_heartbeat_at=None,
            )
        )

    async def create_sample_file(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        original_filename: str,
        content_type: str | None,
    ) -> PlotSampleFile:
        sample_file = PlotSampleFile(
            user_id=user_id,
            original_filename=original_filename,
            content_type=content_type,
            storage_path="",
            byte_size=0,
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
        plot_name: str,
        provider_id: str,
        model_name: str,
        sample_file_id: str,
        pending_status: str,
    ) -> PlotAnalysisJob:
        job = PlotAnalysisJob(
            user_id=user_id,
            plot_name=plot_name,
            provider_id=provider_id,
            model_name=model_name,
            sample_file_id=sample_file_id,
            status=pending_status,
        )
        session.add(job)
        await session.flush()
        return job

    async def flush(self, session: AsyncSession) -> None:
        await session.flush()

    async def delete_job_graph(self, session: AsyncSession, job: PlotAnalysisJob) -> None:
        if job.plot_profile is not None:
            await session.delete(job.plot_profile)
        await session.delete(job)
        if job.sample_file is not None:
            await session.delete(job.sample_file)
        await session.flush()
