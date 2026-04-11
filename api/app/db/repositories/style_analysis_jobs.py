from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer, joinedload

from app.db.models import StyleAnalysisJob, StyleSampleFile


class StyleAnalysisJobRepository:
    async def list(
        self,
        session: AsyncSession,
        *,
        offset: int,
        limit: int,
        include_payloads: bool = False,
    ) -> list[StyleAnalysisJob]:
        stmt = (
            select(StyleAnalysisJob)
            .options(
                joinedload(StyleAnalysisJob.provider),
                joinedload(StyleAnalysisJob.sample_file),
                joinedload(StyleAnalysisJob.style_profile),
            )
            .order_by(StyleAnalysisJob.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if not include_payloads:
            stmt = stmt.options(
                defer(StyleAnalysisJob.analysis_meta_payload),
                defer(StyleAnalysisJob.analysis_report_payload),
                defer(StyleAnalysisJob.style_summary_payload),
                defer(StyleAnalysisJob.prompt_pack_payload),
            )
        result = await session.stream_scalars(stmt)
        return [job async for job in result]

    async def get_by_id(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        include_payloads: bool = True,
    ) -> StyleAnalysisJob | None:
        stmt = select(StyleAnalysisJob).options(
            joinedload(StyleAnalysisJob.provider),
            joinedload(StyleAnalysisJob.sample_file),
            joinedload(StyleAnalysisJob.style_profile),
        )
        if not include_payloads:
            stmt = stmt.options(
                defer(StyleAnalysisJob.analysis_meta_payload),
                defer(StyleAnalysisJob.analysis_report_payload),
                defer(StyleAnalysisJob.style_summary_payload),
                defer(StyleAnalysisJob.prompt_pack_payload),
            )
        return await session.scalar(stmt.where(StyleAnalysisJob.id == job_id))

    async def get_status_and_payload(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        payload_column,
    ):
        row = await session.execute(
            select(StyleAnalysisJob.status, payload_column).where(StyleAnalysisJob.id == job_id)
        )
        return row.one_or_none()

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
        candidate_id = await session.scalar(
            select(StyleAnalysisJob.id)
            .where(
                StyleAnalysisJob.status == pending_status,
                StyleAnalysisJob.attempt_count < max_attempts,
            )
            .order_by(StyleAnalysisJob.created_at.asc())
            .limit(1)
        )
        if candidate_id is None:
            return None

        result = await session.execute(
            update(StyleAnalysisJob)
            .where(
                StyleAnalysisJob.id == candidate_id,
                StyleAnalysisJob.status == pending_status,
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
        )
        if result.rowcount != 1:
            return None
        return candidate_id

    async def heartbeat(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        running_status: str,
        stage: str | None,
        now: datetime,
    ) -> None:
        await session.execute(
            update(StyleAnalysisJob)
            .where(StyleAnalysisJob.id == job_id, StyleAnalysisJob.status == running_status)
            .values(stage=stage, last_heartbeat_at=now)
        )

    async def recover_stale_jobs(
        self,
        session: AsyncSession,
        *,
        cutoff: datetime,
        max_attempts: int,
        running_status: str,
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

        await session.execute(
            update(StyleAnalysisJob)
            .where(stale_condition, StyleAnalysisJob.attempt_count >= max_attempts)
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
        await session.execute(
            update(StyleAnalysisJob)
            .where(stale_condition, StyleAnalysisJob.attempt_count < max_attempts)
            .values(
                status=pending_status,
                stage=None,
                error_message=None,
                locked_by=None,
                locked_at=None,
                last_heartbeat_at=None,
            )
        )

    async def create_sample_file(
        self,
        session: AsyncSession,
        *,
        original_filename: str,
        content_type: str | None,
    ) -> StyleSampleFile:
        sample_file = StyleSampleFile(
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
        style_name: str,
        provider_id: str,
        model_name: str,
        sample_file_id: str,
        pending_status: str,
    ) -> StyleAnalysisJob:
        job = StyleAnalysisJob(
            style_name=style_name,
            provider_id=provider_id,
            model_name=model_name,
            sample_file_id=sample_file_id,
            status=pending_status,
            stage=None,
            error_message=None,
            analysis_meta_payload=None,
            analysis_report_payload=None,
            style_summary_payload=None,
            prompt_pack_payload=None,
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
