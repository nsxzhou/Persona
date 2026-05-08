from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ProjectPromptAsset


class ProjectPromptAssetRepository:
    async def list_by_project_id(
        self,
        session: AsyncSession,
        project_id: str,
    ) -> list[ProjectPromptAsset]:
        stmt = (
            select(ProjectPromptAsset)
            .where(ProjectPromptAsset.project_id == project_id)
            .order_by(
                ProjectPromptAsset.priority.desc(),
                ProjectPromptAsset.created_at.asc(),
                ProjectPromptAsset.id.asc(),
            )
        )
        result = await session.stream_scalars(stmt)
        return [asset async for asset in result]

    async def get_by_id(
        self,
        session: AsyncSession,
        asset_id: str,
        *,
        project_id: str | None = None,
    ) -> ProjectPromptAsset | None:
        stmt = select(ProjectPromptAsset).where(ProjectPromptAsset.id == asset_id)
        if project_id is not None:
            stmt = stmt.where(ProjectPromptAsset.project_id == project_id)
        return await session.scalar(stmt)

    async def create(
        self,
        session: AsyncSession,
        *,
        project_id: str,
        kind: str,
        scope: str,
        chapter_id: str | None,
        title: str,
        content: str,
        keywords: list[str],
        enabled: bool,
        always_on: bool,
        priority: int,
    ) -> ProjectPromptAsset:
        asset = ProjectPromptAsset(
            project_id=project_id,
            kind=kind,
            scope=scope,
            chapter_id=chapter_id,
            title=title,
            content=content,
            keywords_payload=keywords,
            enabled=enabled,
            always_on=always_on,
            priority=priority,
        )
        session.add(asset)
        await session.flush()
        return asset

    async def flush(self, session: AsyncSession) -> None:
        await session.flush()

    async def delete(self, session: AsyncSession, asset: ProjectPromptAsset) -> None:
        await session.delete(asset)
        await session.flush()
