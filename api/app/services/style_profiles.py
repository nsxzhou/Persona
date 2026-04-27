from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain_errors import ConflictError, NotFoundError
from app.db.models import StyleProfile
from app.db.repositories.projects import ProjectRepository
from app.db.repositories.style_profiles import StyleProfileCreateData, StyleProfileRepository
from app.schemas.style_profiles import StyleProfileCreate, StyleProfileUpdate
from app.services.base_profile import BaseProfileService


class StyleProfileService(BaseProfileService[StyleProfile]):
    def __init__(
        self,
        repository: StyleProfileRepository | None = None,
        project_repository: ProjectRepository | None = None,
    ) -> None:
        self.repository = repository or StyleProfileRepository()
        super().__init__(self.repository, profile_name="风格档案")
        self.project_repository = project_repository or ProjectRepository()

    async def _mount_project(
        self,
        session: AsyncSession,
        *,
        project_id: str | None,
        profile_id: str,
        user_id: str | None = None,
    ) -> None:
        if project_id is None:
            return

        project = await self.project_repository.set_style_profile_id_by_project_id(
            session,
            project_id,
            profile_id,
            user_id=user_id,
        )
        if project is None:
            raise NotFoundError("项目不存在")

    async def _check_delete_constraints(self, session: AsyncSession, profile: StyleProfile) -> None:
        if profile.projects:
            raise ConflictError(f"该{self.profile_name}正被项目引用，无法删除")

    async def create(
        self,
        session: AsyncSession,
        payload: StyleProfileCreate,
        *,
        user_id: str | None = None,
    ) -> StyleProfile:
        existing = await self.repository.get_by_source_job_id(
            session, payload.job_id, user_id=user_id
        )
        if existing is not None:
            raise ConflictError("该分析任务已保存为风格档案")

        job = await self.repository.get_job_for_profile_creation(
            session,
            payload.job_id,
            user_id=user_id,
        )
        if job is None:
            raise NotFoundError("分析任务不存在")

        analysis_report = job.analysis_report_payload
        if job.status != "succeeded" or analysis_report is None:
            raise ConflictError("仅已成功完成的分析任务可以保存为风格档案")
        resolved_user_id = user_id or job.user_id

        profile = await self.repository.create(
            session,
            data=StyleProfileCreateData(
                source_job_id=job.id,
                provider_id=job.provider_id,
                model_name=job.model_name,
                source_filename=job.sample_file.original_filename,
                style_name=payload.style_name,
                analysis_report_payload=analysis_report,
                voice_profile_payload=payload.voice_profile_markdown,
                user_id=resolved_user_id,
            ),
        )
        await self._mount_project(
            session,
            project_id=payload.mount_project_id,
            profile_id=profile.id,
            user_id=resolved_user_id,
        )
        return profile

    async def update(
        self,
        session: AsyncSession,
        profile_id: str,
        payload: StyleProfileUpdate,
        *,
        user_id: str | None = None,
    ) -> StyleProfile:
        profile = await self.get_or_404(session, profile_id, user_id=user_id)
        profile.style_name = payload.style_name
        profile.voice_profile_payload = payload.voice_profile_markdown
        await self.repository.flush(session)
        await self._mount_project(
            session,
            project_id=payload.mount_project_id,
            profile_id=profile.id,
            user_id=user_id,
        )
        return profile
