from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain_errors import NotFoundError
from app.db.models import ProjectChapter
from app.db.repositories.project_chapters import ProjectChapterRepository
from app.services.outline_parser import parse_outline
from app.services.projects import ProjectService


class ProjectChapterService:
    def __init__(
        self,
        repository: ProjectChapterRepository | None = None,
        project_service: ProjectService | None = None,
    ) -> None:
        self.repository = repository or ProjectChapterRepository()
        self.project_service = project_service or ProjectService()

    async def list(
        self,
        session: AsyncSession,
        project_id: str,
        *,
        user_id: str,
    ) -> list[ProjectChapter]:
        await self.project_service.get_or_404(session, project_id, user_id=user_id)
        return await self.repository.list_by_project(session, project_id)

    async def sync_outline(
        self,
        session: AsyncSession,
        project_id: str,
        *,
        user_id: str,
    ) -> list[ProjectChapter]:
        project = await self.project_service.get_or_404(
            session, project_id, user_id=user_id,
        )
        parsed = parse_outline(project.outline_detail or "")
        existing_chapters = await self.repository.list_by_project(session, project_id)
        existing_chapter_map = {
            (chapter.volume_index, chapter.chapter_index): chapter
            for chapter in existing_chapters
        }

        for volume_index, volume in enumerate(parsed["volumes"]):
            for chapter_index, chapter_outline in enumerate(volume["chapters"]):
                chapter = existing_chapter_map.get((volume_index, chapter_index))
                title = chapter_outline["title"]
                if chapter is None:
                    chapter = await self.repository.create(
                        session,
                        project_id=project_id,
                        volume_index=volume_index,
                        chapter_index=chapter_index,
                        title=title,
                    )
                    existing_chapters.append(chapter)
                    existing_chapter_map[(volume_index, chapter_index)] = chapter
                elif chapter.title != title:
                    chapter.title = title

        await self.repository.flush(session)
        return sorted(
            existing_chapters,
            key=lambda chapter: (chapter.volume_index, chapter.chapter_index),
        )

    async def update(
        self,
        session: AsyncSession,
        project_id: str,
        chapter_id: str,
        content: str,
        *,
        user_id: str,
    ) -> ProjectChapter:
        await self.project_service.get_or_404(session, project_id, user_id=user_id)
        chapter = await self.repository.get_by_id(
            session, chapter_id, project_id=project_id,
        )
        if chapter is None:
            raise NotFoundError("章节不存在")
        chapter.content = content
        chapter.word_count = len(content)
        await self.repository.flush(session)
        return chapter
