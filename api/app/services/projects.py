from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain_errors import NotFoundError
from app.db.models import Project
from app.db.repositories.projects import ProjectRepository
from app.schemas.projects import ProjectCreate, ProjectUpdate, ProjectBibleUpdate
from app.services.plot_profiles import PlotProfileService
from app.services.provider_configs import ProviderConfigService
from app.services.style_profiles import StyleProfileService


class ProjectService:
    def __init__(
        self,
        repository: ProjectRepository | None = None,
        provider_service: ProviderConfigService | None = None,
        style_profile_service: StyleProfileService | None = None,
        plot_profile_service: PlotProfileService | None = None,
    ) -> None:
        self.repository = repository or ProjectRepository()
        self.provider_service = provider_service or ProviderConfigService()
        self.style_profile_service = style_profile_service or StyleProfileService()
        self.plot_profile_service = plot_profile_service or PlotProfileService()

    async def list(
        self,
        session: AsyncSession,
        *,
        user_id: str | None = None,
        include_archived: bool,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Project]:
        return await self.repository.list(
            session,
            user_id=user_id,
            include_archived=include_archived,
            offset=offset,
            limit=limit,
        )

    async def get_or_404(
        self,
        session: AsyncSession,
        project_id: str,
        *,
        user_id: str | None = None,
    ) -> Project:
        project = await self.repository.get_by_id(session, project_id, user_id=user_id)
        if project is None:
            raise NotFoundError("项目不存在")
        return project

    async def create(
        self,
        session: AsyncSession,
        payload: ProjectCreate,
        *,
        user_id: str | None = None,
    ) -> Project:
        provider = await self.provider_service.ensure_enabled(
            session,
            payload.default_provider_id,
            user_id=user_id,
        )
        resolved_user_id = user_id or provider.user_id
        if payload.style_profile_id is not None:
            await self.style_profile_service.get_or_404(
                session,
                payload.style_profile_id,
                user_id=resolved_user_id,
            )
        if payload.plot_profile_id is not None:
            await self.plot_profile_service.get_or_404(
                session,
                payload.plot_profile_id,
                user_id=resolved_user_id,
            )
        default_model = payload.default_model.strip() if payload.default_model else ""
        payload.default_provider_id = provider.id
        payload.default_model = default_model or provider.default_model

        project = await self.repository.create(
            session,
            user_id=resolved_user_id,
            name=payload.name,
            description=payload.description,
            status=payload.status,
            default_provider_id=payload.default_provider_id,
            default_model=payload.default_model,
            style_profile_id=payload.style_profile_id,
            plot_profile_id=payload.plot_profile_id,
            generation_profile_payload=(
                payload.generation_profile.model_dump(mode="json")
                if payload.generation_profile is not None
                else None
            ),
            length_preset=payload.length_preset,
            auto_sync_memory=payload.auto_sync_memory,
        )
        await self.repository.refresh_provider(session, project)
        return await self.get_or_404(session, project.id, user_id=resolved_user_id)

    async def update(
        self,
        session: AsyncSession,
        project_id: str,
        payload: ProjectUpdate,
        *,
        user_id: str | None = None,
    ) -> Project:
        project = await self.get_or_404(session, project_id, user_id=user_id)
        data = payload.model_dump(exclude_unset=True)

        if "default_provider_id" in data and data["default_provider_id"]:
            provider = await self.provider_service.ensure_enabled(
                session,
                data.pop("default_provider_id"),
                user_id=user_id,
            )
            project.default_provider_id = provider.id
            if data.get("default_model") is None:
                project.default_model = provider.default_model
        else:
            data.pop("default_provider_id", None)

        if "style_profile_id" in data:
            style_profile_id = data.pop("style_profile_id")
            if style_profile_id is not None:
                await self.style_profile_service.get_or_404(
                    session,
                    style_profile_id,
                    user_id=user_id,
                )
            project.style_profile_id = style_profile_id

        if "plot_profile_id" in data:
            plot_profile_id = data.pop("plot_profile_id")
            if plot_profile_id is not None:
                await self.plot_profile_service.get_or_404(
                    session,
                    plot_profile_id,
                    user_id=user_id,
                )
            project.plot_profile_id = plot_profile_id

        if "default_model" in data:
            default_model = (data.pop("default_model") or "").strip()
            project.default_model = default_model or project.provider.default_model

        if "generation_profile" in data:
            generation_profile = data.pop("generation_profile")
            project.generation_profile_payload = (
                generation_profile.model_dump(mode="json")
                if generation_profile is not None
                else None
            )

        _ASSIGNABLE_FIELDS = {
            "name", "description", "status", "length_preset",
            "auto_sync_memory",
        }
        for field, value in data.items():
            if field in _ASSIGNABLE_FIELDS:
                setattr(project, field, value)

        await self.repository.flush(session)
        return await self.get_or_404(session, project.id, user_id=user_id)

    async def get_bible_or_404(
        self,
        session: AsyncSession,
        project_id: str,
        *,
        user_id: str | None = None,
    ):
        # ensure user owns the project
        await self.get_or_404(session, project_id, user_id=user_id)
        bible = await self.repository.get_bible_by_project_id(session, project_id)
        if bible is None:
            raise NotFoundError("项目 Bible 不存在")
        return bible

    async def update_bible(
        self,
        session: AsyncSession,
        project_id: str,
        payload: ProjectBibleUpdate,
        *,
        user_id: str | None = None,
    ):
        bible = await self.get_bible_or_404(session, project_id, user_id=user_id)
        data = payload.model_dump(exclude_unset=True)

        _BIBLE_ASSIGNABLE_FIELDS = {
            "inspiration", "world_building", "characters",
            "outline_master", "outline_detail",
            "runtime_state", "runtime_threads",
        }
        for field, value in data.items():
            if field in _BIBLE_ASSIGNABLE_FIELDS:
                setattr(bible, field, value)

        await self.repository.flush(session)
        return bible

    async def archive(
        self,
        session: AsyncSession,
        project_id: str,
        *,
        user_id: str | None = None,
    ) -> Project:
        project = await self.get_or_404(session, project_id, user_id=user_id)
        project.archived_at = datetime.now(UTC)
        await self.repository.flush(session)
        return project

    async def restore(
        self,
        session: AsyncSession,
        project_id: str,
        *,
        user_id: str | None = None,
    ) -> Project:
        project = await self.get_or_404(session, project_id, user_id=user_id)
        project.archived_at = None
        await self.repository.flush(session)
        return project

    async def delete(
        self,
        session: AsyncSession,
        project_id: str,
        *,
        user_id: str | None = None,
    ) -> None:
        project = await self.get_or_404(session, project_id, user_id=user_id)
        await self.repository.delete(session, project)
