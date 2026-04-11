from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import Project


class ProjectRepository:
    async def list(
        self,
        session: AsyncSession,
        *,
        user_id: str | None = None,
        include_archived: bool,
    ) -> list[Project]:
        query = (
            select(Project)
            .options(joinedload(Project.provider))
            .order_by(Project.created_at.desc())
        )
        if user_id is not None:
            query = query.where(Project.user_id == user_id)
        if not include_archived:
            query = query.where(Project.archived_at.is_(None))
        result = await session.stream_scalars(query)
        return [project async for project in result]

    async def get_by_id(
        self,
        session: AsyncSession,
        project_id: str,
        *,
        user_id: str | None = None,
    ) -> Project | None:
        stmt = (
            select(Project)
            .options(joinedload(Project.provider))
            .where(Project.id == project_id)
        )
        if user_id is not None:
            stmt = stmt.where(Project.user_id == user_id)
        return await session.scalar(
            stmt
        )

    async def create(
        self,
        session: AsyncSession,
        *,
        name: str,
        description: str,
        status: str,
        default_provider_id: str,
        default_model: str,
        style_profile_id: str | None,
        user_id: str,
    ) -> Project:
        project = Project(
            name=name,
            description=description,
            status=status,
            default_provider_id=default_provider_id,
            default_model=default_model,
            style_profile_id=style_profile_id,
            user_id=user_id,
        )
        session.add(project)
        await session.flush()
        return project

    async def refresh_provider(self, session: AsyncSession, project: Project) -> None:
        await session.refresh(project, attribute_names=["provider"])

    async def set_style_profile_id_by_project_id(
        self,
        session: AsyncSession,
        project_id: str,
        style_profile_id: str | None,
        *,
        user_id: str | None = None,
    ) -> Project | None:
        project = await self.get_by_id(session, project_id, user_id=user_id)
        if project is None:
            return None
        project.style_profile_id = style_profile_id
        await session.flush()
        return project

    async def flush(self, session: AsyncSession) -> None:
        await session.flush()
