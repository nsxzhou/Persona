from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import StyleAnalysisJob, StyleProfile
from app.schemas.style_analysis_jobs import StyleDraft
from app.schemas.style_profiles import StyleProfileCreate


class StyleProfileService:
    async def list(self, session: AsyncSession) -> list[StyleProfile]:
        result = await session.scalars(
            select(StyleProfile).order_by(StyleProfile.created_at.desc())
        )
        return list(result.all())

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
                selectinload(StyleAnalysisJob.sample_file),
                selectinload(StyleAnalysisJob.provider),
            )
            .where(StyleAnalysisJob.id == payload.job_id)
        )
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分析任务不存在")
        if job.status != "succeeded" or job.draft_payload is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="仅已成功完成的分析任务可以保存为风格档案",
            )

        normalized = StyleDraft(
            style_name=payload.style_name,
            analysis_summary=payload.analysis_summary,
            global_system_prompt=payload.global_system_prompt,
            dimensions=payload.dimensions,
            scene_prompts=payload.scene_prompts,
            few_shot_examples=payload.few_shot_examples,
        )
        profile = StyleProfile(
            source_job_id=job.id,
            provider_id=job.provider_id,
            model_name=job.model_name,
            source_filename=job.sample_file.original_filename,
            style_name=normalized.style_name,
            analysis_summary=normalized.analysis_summary,
            global_system_prompt=normalized.global_system_prompt,
            dimensions=normalized.dimensions.model_dump(mode="json"),
            scene_prompts=normalized.scene_prompts.model_dump(mode="json"),
            few_shot_examples=[item.model_dump(mode="json") for item in normalized.few_shot_examples],
        )
        session.add(profile)
        await session.flush()
        return profile

