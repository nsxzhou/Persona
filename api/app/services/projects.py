from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Project, ProviderConfig
from app.schemas.projects import ProjectCreate, ProjectUpdate
from app.services.provider_configs import ProviderConfigService


class ProjectService:
    def __init__(self) -> None:
        self.provider_service = ProviderConfigService()

    async def list(self, session: AsyncSession, *, include_archived: bool) -> list[Project]:
        query = select(Project).options(selectinload(Project.provider)).order_by(Project.created_at.desc())
        if not include_archived:
            query = query.where(Project.archived_at.is_(None))
        result = await session.scalars(query)
        return list(result.all())

    async def get_or_404(self, session: AsyncSession, project_id: str) -> Project:
        project = await session.scalar(
            select(Project).options(selectinload(Project.provider)).where(Project.id == project_id)
        )
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
        return project

    async def create(self, session: AsyncSession, payload: ProjectCreate) -> Project:
        provider = await self.provider_service.ensure_enabled(session, payload.default_provider_id)
        default_model = payload.default_model.strip() if payload.default_model else ""
        project = Project(
            name=payload.name,
            description=payload.description,
            status=payload.status,
            default_provider_id=provider.id,
            default_model=default_model or provider.default_model,
            style_profile_id=payload.style_profile_id,
        )
        session.add(project)
        await session.flush()
        await session.refresh(project, attribute_names=["provider"])
        return await self.get_or_404(session, project.id)

    async def update(self, session: AsyncSession, project_id: str, payload: ProjectUpdate) -> Project:
        project = await self.get_or_404(session, project_id)
        data = payload.model_dump(exclude_unset=True)

        provider: ProviderConfig = project.provider
        if "default_provider_id" in data and data["default_provider_id"]:
            provider = await self.provider_service.ensure_enabled(session, data["default_provider_id"])
            project.default_provider_id = provider.id

        if "name" in data:
            project.name = data["name"]
        if "description" in data:
            project.description = data["description"]
        if "status" in data:
            project.status = data["status"]
        if "style_profile_id" in data:
            project.style_profile_id = data["style_profile_id"]
        if "default_model" in data:
            default_model = (data["default_model"] or "").strip()
            project.default_model = default_model or provider.default_model

        await session.flush()
        return await self.get_or_404(session, project.id)

    async def archive(self, session: AsyncSession, project_id: str) -> Project:
        project = await self.get_or_404(session, project_id)
        project.archived_at = datetime.now(UTC)
        await session.flush()
        return project

    async def restore(self, session: AsyncSession, project_id: str) -> Project:
        project = await self.get_or_404(session, project_id)
        project.archived_at = None
        await session.flush()
        return project

