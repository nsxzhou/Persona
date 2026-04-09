from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import StyleAnalysisJob, StyleProfile
from app.schemas.style_analysis_jobs import PromptPack, StyleSummary
from app.schemas.style_profiles import StyleProfileCreate, StyleProfileUpdate
from app.services.style_analysis_jobs import build_job_result_bundle


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
                selectinload(StyleAnalysisJob.style_profile),
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
            analysis_summary=style_summary.style_positioning,
            global_system_prompt=prompt_pack.system_prompt,
            dimensions={
                "core_features": style_summary.core_features,
                "lexical_preferences": style_summary.lexical_preferences,
                "rhythm_profile": style_summary.rhythm_profile,
                "punctuation_profile": style_summary.punctuation_profile,
                "imagery_and_themes": style_summary.imagery_and_themes,
            },
            scene_prompts=prompt_pack.scene_prompts.model_dump(mode="json"),
            few_shot_examples=[item.model_dump(mode="json") for item in prompt_pack.few_shot_slots],
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
        profile.analysis_summary = style_summary.style_positioning
        profile.global_system_prompt = prompt_pack.system_prompt
        profile.dimensions = {
            "core_features": style_summary.core_features,
            "lexical_preferences": style_summary.lexical_preferences,
            "rhythm_profile": style_summary.rhythm_profile,
            "punctuation_profile": style_summary.punctuation_profile,
            "imagery_and_themes": style_summary.imagery_and_themes,
        }
        profile.scene_prompts = prompt_pack.scene_prompts.model_dump(mode="json")
        profile.few_shot_examples = [
            item.model_dump(mode="json") for item in prompt_pack.few_shot_slots
        ]
        profile.style_summary_payload = style_summary.model_dump(mode="json")
        profile.prompt_pack_payload = prompt_pack.model_dump(mode="json")
        await session.flush()
        return profile
