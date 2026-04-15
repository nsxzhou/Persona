from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain_errors import NotFoundError
from app.db.models import Project, ProviderConfig
from app.db.repositories.projects import ProjectRepository
from app.schemas.projects import ProjectCreate, ProjectUpdate
from app.services.provider_configs import ProviderConfigService
from app.services.style_profiles import StyleProfileService


class ProjectService:
    def __init__(
        self,
        repository: ProjectRepository | None = None,
        provider_service: ProviderConfigService | None = None,
        style_profile_service: StyleProfileService | None = None,
    ) -> None:
        self.repository = repository or ProjectRepository()
        self.provider_service = provider_service or ProviderConfigService()
        self.style_profile_service = style_profile_service or StyleProfileService()

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
        default_model = payload.default_model.strip() if payload.default_model else ""
        payload.default_provider_id = provider.id
        payload.default_model = default_model or provider.default_model

        project = await self.repository.create(
            session,
            payload,
            user_id=resolved_user_id,
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

        provider: ProviderConfig = project.provider
        if "default_provider_id" in data and data["default_provider_id"]:
            provider = await self.provider_service.ensure_enabled(
                session,
                data["default_provider_id"],
                user_id=user_id,
            )
            project.default_provider_id = provider.id

        if "name" in data:
            project.name = data["name"]
        if "description" in data:
            project.description = data["description"]
        if "status" in data:
            project.status = data["status"]
        if "style_profile_id" in data:
            if data["style_profile_id"] is not None:
                await self.style_profile_service.get_or_404(
                    session,
                    data["style_profile_id"],
                    user_id=user_id,
                )
            project.style_profile_id = data["style_profile_id"]
        if "default_model" in data:
            default_model = (data["default_model"] or "").strip()
            project.default_model = default_model or provider.default_model
        if "content" in data:
            project.content = data["content"]
        for field in (
            "inspiration", "world_building", "characters",
            "outline_master", "outline_detail", "story_bible",
        ):
            if field in data:
                setattr(project, field, data[field])

        await self.repository.flush(session)
        return await self.get_or_404(session, project.id, user_id=user_id)

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
