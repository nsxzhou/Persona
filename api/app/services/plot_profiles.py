from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain_errors import ConflictError, NotFoundError
from app.db.models import PlotProfile
from app.db.repositories.plot_profiles import PlotProfileCreateData, PlotProfileRepository
from app.db.repositories.projects import ProjectRepository
from app.schemas.plot_profiles import PlotProfileCreate, PlotProfileUpdate
from app.services.base_profile import BaseProfileService


class PlotProfileService(BaseProfileService[PlotProfile]):
    def __init__(
        self,
        repository: PlotProfileRepository | None = None,
        project_repository: ProjectRepository | None = None,
    ) -> None:
        self.repository = repository or PlotProfileRepository()
        super().__init__(self.repository, profile_name="情节档案")
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

        project = await self.project_repository.set_plot_profile_id_by_project_id(
            session,
            project_id,
            profile_id,
            user_id=user_id,
        )
        if project is None:
            raise NotFoundError("项目不存在")

    async def create(
        self,
        session: AsyncSession,
        payload: PlotProfileCreate,
        *,
        user_id: str | None = None,
    ) -> PlotProfile:
        existing = await self.repository.get_by_source_job_id(
            session, payload.job_id, user_id=user_id
        )
        if existing is not None:
            raise ConflictError("该分析任务已保存为情节档案")

        job = await self.repository.get_job_for_profile_creation(
            session,
            payload.job_id,
            user_id=user_id,
        )
        if job is None:
            raise NotFoundError("分析任务不存在")

        analysis_report = job.analysis_report_payload
        if job.status != "succeeded" or analysis_report is None:
            raise ConflictError("仅已成功完成的分析任务可以保存为情节档案")
        resolved_user_id = user_id or job.user_id

        skeleton_payload = (
            payload.plot_skeleton_markdown
            if payload.plot_skeleton_markdown is not None
            else job.plot_skeleton_payload
        )
        profile = await self.repository.create(
            session,
            data=PlotProfileCreateData(
                source_job_id=job.id,
                provider_id=job.provider_id,
                model_name=job.model_name,
                source_filename=job.sample_file.original_filename,
                plot_name=payload.plot_name,
                analysis_report_payload=analysis_report,
                story_engine_payload=payload.story_engine_markdown,
                plot_skeleton_payload=skeleton_payload,
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
        payload: PlotProfileUpdate,
        *,
        user_id: str | None = None,
    ) -> PlotProfile:
        profile = await self.get_or_404(session, profile_id, user_id=user_id)
        profile.plot_name = payload.plot_name
        profile.story_engine_payload = payload.story_engine_markdown
        if payload.plot_skeleton_markdown is not None:
            profile.plot_skeleton_payload = payload.plot_skeleton_markdown
        await self.repository.flush(session)
        await self._mount_project(
            session,
            project_id=payload.mount_project_id,
            profile_id=profile.id,
            user_id=user_id,
        )
        return profile
