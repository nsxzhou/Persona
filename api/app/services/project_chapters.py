from __future__ import annotations

import hashlib

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

    @staticmethod
    def _hash_content(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _clear_memory_sync(chapter: ProjectChapter) -> None:
        chapter.memory_sync_status = None
        chapter.memory_sync_source = None
        chapter.memory_sync_scope = None
        chapter.memory_sync_checked_at = None
        chapter.memory_sync_checked_content_hash = None
        chapter.memory_sync_error_message = None
        chapter.memory_sync_proposed_state = None
        chapter.memory_sync_proposed_threads = None

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
        await self.project_service.get_or_404(
            session, project_id, user_id=user_id,
        )
        bible = await self.project_service.get_bible_or_404(
            session, project_id, user_id=user_id,
        )
        parsed = parse_outline(bible.outline_detail or "")
        existing_chapters = await self.repository.list_by_project(session, project_id)
        existing_chapter_map = {
            (chapter.volume_index, chapter.chapter_index): chapter
            for chapter in existing_chapters
        }

        new_chapters: list[ProjectChapter] = []
        for volume_index, volume in enumerate(parsed["volumes"]):
            for chapter_index, chapter_outline in enumerate(volume["chapters"]):
                chapter = existing_chapter_map.get((volume_index, chapter_index))
                title = chapter_outline["title"]
                if chapter is None:
                    chapter = ProjectChapter(
                        project_id=project_id,
                        volume_index=volume_index,
                        chapter_index=chapter_index,
                        title=title,
                    )
                    new_chapters.append(chapter)
                    existing_chapters.append(chapter)
                    existing_chapter_map[(volume_index, chapter_index)] = chapter
                elif chapter.title != title:
                    chapter.title = title

        if new_chapters:
            session.add_all(new_chapters)

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
        payload,
        *,
        user_id: str,
    ) -> ProjectChapter:
        await self.project_service.get_or_404(session, project_id, user_id=user_id)
        chapter = await self.repository.get_by_id(
            session, chapter_id, project_id=project_id,
        )
        if chapter is None:
            raise NotFoundError("章节不存在")
        update_data = payload.model_dump(exclude_unset=True)

        if "content" in update_data:
            content = update_data["content"] or ""
            chapter.content = content
            chapter.word_count = len(content)
            if chapter.memory_sync_checked_content_hash != self._hash_content(content):
                self._clear_memory_sync(chapter)

        for field in (
            "memory_sync_status",
            "memory_sync_source",
            "memory_sync_scope",
            "memory_sync_checked_at",
            "memory_sync_checked_content_hash",
            "memory_sync_error_message",
            "memory_sync_proposed_state",
            "memory_sync_proposed_threads",
        ):
            if field in update_data:
                setattr(chapter, field, update_data[field])
        await self.repository.flush(session)
        return chapter
