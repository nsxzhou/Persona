from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer, joinedload

from app.db.models import StyleAnalysisJob, StyleProfile
from app.schemas.style_analysis_jobs import PromptPack, StyleSummary
from app.schemas.style_profiles import StyleProfileCreate, StyleProfileUpdate
from app.services.style_analysis_jobs import build_job_result_bundle


class StyleProfileService:
    async def list(
        self,
        session: AsyncSession,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> list[StyleProfile]:
        limit = min(max(limit, 1), 100)
        result = await session.stream_scalars(
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
        return [p async for p in result]

    async def get_or_404(self, session: AsyncSession, profile_id: str) -> StyleProfile:
        profile = await session.get(StyleProfile, profile_id)
        if profile is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="风格档案不存在")
        return profile

    async def create(self, session: AsyncSession, payload: StyleProfileCreate) -> StyleProfile:
        existing = await session.scalar(
            select(StyleProfile).where(StyleProfile.source_job_id == payload.job_id)
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="该分析任务已保存为风格档案",
            )

        job = await session.scalar(
            select(StyleAnalysisJob)
            .options(
                joinedload(StyleAnalysisJob.sample_file),
                joinedload(StyleAnalysisJob.provider),
                joinedload(StyleAnalysisJob.style_profile),
            )
            .where(StyleAnalysisJob.id == payload.job_id)
        )
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分析任务不存在")

        _, analysis_report, _, _ = build_job_result_bundle(job)
        if job.status != "succeeded" or analysis_report is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="仅已成功完成的分析任务可以保存为风格档案",
            )

        style_summary = StyleSummary.model_validate(payload.style_summary)
        prompt_pack = PromptPack.model_validate(payload.prompt_pack)

        profile = StyleProfile(
            source_job_id=job.id,
            provider_id=job.provider_id,
            model_name=job.model_name,
            source_filename=job.sample_file.original_filename,
            style_name=style_summary.style_name,
            analysis_report_payload=analysis_report.model_dump(mode="json"),
            style_summary_payload=style_summary.model_dump(mode="json"),
            prompt_pack_payload=prompt_pack.model_dump(mode="json"),
        )
        session.add(profile)
        await session.flush()
        return profile

    async def update(
        self,
        session: AsyncSession,
        profile_id: str,
        payload: StyleProfileUpdate,
    ) -> StyleProfile:
        profile = await self.get_or_404(session, profile_id)
        style_summary = StyleSummary.model_validate(payload.style_summary)
        prompt_pack = PromptPack.model_validate(payload.prompt_pack)

        profile.style_name = style_summary.style_name
        profile.style_summary_payload = style_summary.model_dump(mode="json")
        profile.prompt_pack_payload = prompt_pack.model_dump(mode="json")
        await session.flush()
        return profile
