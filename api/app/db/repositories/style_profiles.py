from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer, joinedload, selectinload

from app.db.models import StyleAnalysisJob, StyleProfile


class StyleProfileRepository:
    async def list(
        self,
        session: AsyncSession,
        *,
        user_id: str | None = None,
        offset: int,
        limit: int,
    ) -> list[StyleProfile]:
        stmt = (
            select(StyleProfile)
            .options(
                defer(StyleProfile.analysis_report_payload),
                defer(StyleProfile.style_summary_payload),
                defer(StyleProfile.prompt_pack_payload),
            )
            .order_by(StyleProfile.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if user_id is not None:
            stmt = stmt.where(StyleProfile.user_id == user_id)
        result = await session.stream_scalars(stmt)
        return [profile async for profile in result]

    async def get_by_id(
        self,
        session: AsyncSession,
        profile_id: str,
        *,
        user_id: str | None = None,
    ) -> StyleProfile | None:
        stmt = select(StyleProfile).where(StyleProfile.id == profile_id)
        if user_id is not None:
            stmt = stmt.where(StyleProfile.user_id == user_id)
        return await session.scalar(stmt)

    async def get_with_projects(
        self,
        session: AsyncSession,
        profile_id: str,
        *,
        user_id: str | None = None,
    ) -> StyleProfile | None:
        stmt = (
            select(StyleProfile)
            .options(selectinload(StyleProfile.projects))
            .where(StyleProfile.id == profile_id)
        )
        if user_id is not None:
            stmt = stmt.where(StyleProfile.user_id == user_id)
        return await session.scalar(stmt)

    async def get_by_source_job_id(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str | None = None,
    ) -> StyleProfile | None:
        stmt = select(StyleProfile).where(StyleProfile.source_job_id == job_id)
        if user_id is not None:
            stmt = stmt.where(StyleProfile.user_id == user_id)
        return await session.scalar(stmt)

    async def get_job_for_profile_creation(
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
                joinedload(StyleAnalysisJob.provider),
                joinedload(StyleAnalysisJob.style_profile),
            )
            .where(StyleAnalysisJob.id == job_id)
        )
        if user_id is not None:
            stmt = stmt.where(StyleAnalysisJob.user_id == user_id)
        return await session.scalar(stmt)

    async def create(
        self,
        session: AsyncSession,
        *,
        source_job_id: str,
        provider_id: str,
        model_name: str,
        source_filename: str,
        style_name: str,
        analysis_report_payload: dict,
        style_summary_payload: dict,
        prompt_pack_payload: dict,
        user_id: str,
    ) -> StyleProfile:
        profile = StyleProfile(
            source_job_id=source_job_id,
            provider_id=provider_id,
            model_name=model_name,
            source_filename=source_filename,
            style_name=style_name,
            analysis_report_payload=analysis_report_payload,
            style_summary_payload=style_summary_payload,
            prompt_pack_payload=prompt_pack_payload,
            user_id=user_id,
        )
        session.add(profile)
        await session.flush()
        return profile

    async def flush(self, session: AsyncSession) -> None:
        await session.flush()

    async def delete(self, session: AsyncSession, profile: StyleProfile) -> None:
        await session.delete(profile)
