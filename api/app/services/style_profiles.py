from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import StyleAnalysisJob, StyleProfile
from app.db.repositories.style_profiles import StyleProfileRepository
from app.schemas.style_analysis_jobs import PromptPack, StyleSummary
from app.schemas.style_profiles import StyleProfileCreate, StyleProfileUpdate
from app.services.style_analysis_jobs import build_job_result_bundle


class StyleProfileService:
    def __init__(self, repository: StyleProfileRepository | None = None) -> None:
        self.repository = repository or StyleProfileRepository()

    async def list(
        self,
        session: AsyncSession,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> list[StyleProfile]:
        limit = min(max(limit, 1), 100)
        return await self.repository.list(session, offset=offset, limit=limit)

    async def get_or_404(self, session: AsyncSession, profile_id: str) -> StyleProfile:
        profile = await self.repository.get_by_id(session, profile_id)
        if profile is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="风格档案不存在")
        return profile

    async def _mount_project(
        self,
        session: AsyncSession,
        *,
        project_id: str | None,
        profile_id: str,
    ) -> None:
        if project_id is None:
            return

        from app.services.projects import ProjectService

        await ProjectService().set_style_profile_id(session, project_id, profile_id)

    async def create(self, session: AsyncSession, payload: StyleProfileCreate) -> StyleProfile:
        existing = await self.repository.get_by_source_job_id(session, payload.job_id)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="该分析任务已保存为风格档案",
            )

        job = await self.repository.get_job_for_profile_creation(session, payload.job_id)
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

        profile = await self.repository.create(
            session,
            source_job_id=job.id,
            provider_id=job.provider_id,
            model_name=job.model_name,
            source_filename=job.sample_file.original_filename,
            style_name=style_summary.style_name,
            analysis_report_payload=analysis_report.model_dump(mode="json"),
            style_summary_payload=style_summary.model_dump(mode="json"),
            prompt_pack_payload=prompt_pack.model_dump(mode="json"),
        )
        await self._mount_project(
            session,
            project_id=payload.mount_project_id,
            profile_id=profile.id,
        )
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
        await self.repository.flush(session)
        await self._mount_project(
            session,
            project_id=payload.mount_project_id,
            profile_id=profile.id,
        )
        return profile
