from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ProjectChapter


class ProjectChapterRepository:
    async def list_by_project(
        self,
        session: AsyncSession,
        project_id: str,
    ) -> list[ProjectChapter]:
        result = await session.stream_scalars(
            select(ProjectChapter)
            .where(ProjectChapter.project_id == project_id)
            .order_by(ProjectChapter.volume_index, ProjectChapter.chapter_index)
        )
        return [chapter async for chapter in result]

    async def get_by_id(
        self,
        session: AsyncSession,
        chapter_id: str,
        *,
        project_id: str,
    ) -> ProjectChapter | None:
        return await session.scalar(
            select(ProjectChapter).where(
                ProjectChapter.id == chapter_id,
                ProjectChapter.project_id == project_id,
            )
        )

    async def get_by_position(
        self,
        session: AsyncSession,
        project_id: str,
        volume_index: int,
        chapter_index: int,
    ) -> ProjectChapter | None:
        return await session.scalar(
            select(ProjectChapter).where(
                ProjectChapter.project_id == project_id,
                ProjectChapter.volume_index == volume_index,
                ProjectChapter.chapter_index == chapter_index,
            )
        )

    async def create(
        self,
        session: AsyncSession,
        *,
        project_id: str,
        volume_index: int,
        chapter_index: int,
        title: str,
        content: str = "",
    ) -> ProjectChapter:
        chapter = ProjectChapter(
            project_id=project_id,
            volume_index=volume_index,
            chapter_index=chapter_index,
            title=title,
            content=content,
            word_count=len(content),
        )
        session.add(chapter)
        await session.flush()
        return chapter

    async def flush(self, session: AsyncSession) -> None:
        await session.flush()
