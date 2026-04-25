from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer, joinedload, selectinload

from app.db.models import PlotAnalysisJob, PlotProfile


@dataclass(frozen=True)
class PlotProfileCreateData:
    source_job_id: str
    provider_id: str
    model_name: str
    source_filename: str
    plot_name: str
    analysis_report_payload: str
    prompt_pack_payload: str
    user_id: str
    plot_skeleton_payload: str | None = None


class PlotProfileRepository:
    async def list(
        self,
        session: AsyncSession,
        *,
        user_id: str | None = None,
        offset: int,
        limit: int,
    ) -> list[PlotProfile]:
        stmt = (
            select(PlotProfile)
            .options(
                defer(PlotProfile.analysis_report_payload),
                defer(PlotProfile.plot_summary_payload),
                defer(PlotProfile.prompt_pack_payload),
                defer(PlotProfile.plot_skeleton_payload),
            )
            .order_by(PlotProfile.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if user_id is not None:
            stmt = stmt.where(PlotProfile.user_id == user_id)
        result = await session.stream_scalars(stmt)
        return [profile async for profile in result]

    async def get_by_id(
        self,
        session: AsyncSession,
        profile_id: str,
        *,
        user_id: str | None = None,
    ) -> PlotProfile | None:
        stmt = select(PlotProfile).where(PlotProfile.id == profile_id)
        if user_id is not None:
            stmt = stmt.where(PlotProfile.user_id == user_id)
        return await session.scalar(stmt)

    async def get_with_projects(
        self,
        session: AsyncSession,
        profile_id: str,
        *,
        user_id: str | None = None,
    ) -> PlotProfile | None:
        stmt = (
            select(PlotProfile)
            .options(selectinload(PlotProfile.projects))
            .where(PlotProfile.id == profile_id)
        )
        if user_id is not None:
            stmt = stmt.where(PlotProfile.user_id == user_id)
        return await session.scalar(stmt)

    async def get_by_source_job_id(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str | None = None,
    ) -> PlotProfile | None:
        stmt = select(PlotProfile).where(PlotProfile.source_job_id == job_id)
        if user_id is not None:
            stmt = stmt.where(PlotProfile.user_id == user_id)
        return await session.scalar(stmt)

    async def get_job_for_profile_creation(
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
                joinedload(PlotAnalysisJob.provider),
                joinedload(PlotAnalysisJob.plot_profile),
            )
            .where(PlotAnalysisJob.id == job_id)
        )
        if user_id is not None:
            stmt = stmt.where(PlotAnalysisJob.user_id == user_id)
        return await session.scalar(stmt)

    async def create(
        self,
        session: AsyncSession,
        *,
        data: PlotProfileCreateData,
    ) -> PlotProfile:
        profile = PlotProfile(
            source_job_id=data.source_job_id,
            provider_id=data.provider_id,
            model_name=data.model_name,
            source_filename=data.source_filename,
            plot_name=data.plot_name,
            analysis_report_payload=data.analysis_report_payload,
            plot_summary_payload="",
            prompt_pack_payload=data.prompt_pack_payload,
            plot_skeleton_payload=data.plot_skeleton_payload,
            user_id=data.user_id,
        )
        session.add(profile)
        await session.flush()
        return profile

    async def flush(self, session: AsyncSession) -> None:
        await session.flush()

    async def delete(self, session: AsyncSession, profile: PlotProfile) -> None:
        await session.delete(profile)
