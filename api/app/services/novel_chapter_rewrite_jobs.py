from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain_errors import ConflictError, UnprocessableEntityError
from app.db.models import NovelWorkflowRun, ProjectChapter
from app.db.repositories.project_chapters import ProjectChapterRepository
from app.schemas.novel_chapter_rewrite_jobs import NovelChapterRewriteJobCreateRequest
from app.schemas.novel_workflows import (
    NOVEL_WORKFLOW_STATUS_SUCCEEDED,
    NovelWorkflowCreateRequest,
    NovelWorkflowLogsResponse,
    NovelWorkflowModelOverrides,
)
from app.schemas.project_chapters import ProjectChapterUpdate
from app.services.novel_workflows import NovelWorkflowService
from app.services.project_chapters import ProjectChapterService

CHAPTER_REWRITE_INTENT = "chapter_enrichment_rewrite"
IMPORTED_CHAPTER_FULL_REWRITE_INTENT = "imported_chapter_full_rewrite"
CHAPTER_REWRITE_ARTIFACT = "chapter_rewrite_markdown"
_MAX_CHAPTER_REWRITE_CHARS = 80_000
_ADJACENT_CONTEXT_CHARS = 2_000


class NovelChapterRewriteJobService:
    def __init__(
        self,
        *,
        workflow_service: NovelWorkflowService | None = None,
        chapter_service: ProjectChapterService | None = None,
        chapter_repository: ProjectChapterRepository | None = None,
    ) -> None:
        self.workflow_service = workflow_service or NovelWorkflowService()
        self.chapter_service = chapter_service or ProjectChapterService()
        self.chapter_repository = chapter_repository or ProjectChapterRepository()

    async def create(
        self,
        session: AsyncSession,
        payload: NovelChapterRewriteJobCreateRequest,
        *,
        user_id: str,
    ) -> NovelWorkflowRun:
        chapter = await self.chapter_service.get_or_404(
            session,
            payload.project_id,
            payload.chapter_id,
            user_id=user_id,
        )
        project = await self.chapter_service.project_service.get_or_404(
            session,
            payload.project_id,
            user_id=user_id,
        )
        if not chapter.content.strip():
            raise UnprocessableEntityError("当前章节正文为空，无法改写")
        if len(chapter.content) > _MAX_CHAPTER_REWRITE_CHARS:
            raise UnprocessableEntityError("当前章节过长，v1 暂不支持自动分块改写")
        project_origin = project.project_origin
        intent_type = (
            IMPORTED_CHAPTER_FULL_REWRITE_INTENT
            if project_origin == "txt_import_rewrite"
            else CHAPTER_REWRITE_INTENT
        )
        previous_context, next_context = await self._adjacent_chapter_context(
            session,
            chapter,
            project_origin=project_origin,
        )
        return await self.workflow_service.create(
            session,
            NovelWorkflowCreateRequest(
                intent_type=intent_type,
                project_id=payload.project_id,
                chapter_id=payload.chapter_id,
                rewrite_instruction=payload.instruction.strip(),
                selected_text=chapter.content,
                text_before_cursor=chapter.content,
                current_chapter_context=chapter.summary or chapter.title,
                imported_previous_chapter=previous_context,
                imported_next_chapter=next_context,
                model_overrides=NovelWorkflowModelOverrides(enable_editor_pass=False),
                total_content_length=chapter.word_count,
                expansion_ratio_percent=payload.expansion_ratio_percent,
            ),
            user_id=user_id,
        )

    async def get_status_or_404(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str,
    ) -> NovelWorkflowRun:
        run = await self.workflow_service.get_status_or_404(
            session,
            job_id,
            user_id=user_id,
        )
        self._ensure_chapter_rewrite_run(run)
        return run

    async def get_logs_or_404(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str,
        offset: int = 0,
    ) -> NovelWorkflowLogsResponse:
        run = await self.workflow_service.get_or_404(session, job_id, user_id=user_id)
        self._ensure_chapter_rewrite_run(run)
        return await self.workflow_service.get_job_logs_or_404(
            session,
            job_id,
            user_id=user_id,
            offset=offset,
        )

    async def get_artifact_or_404(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str,
    ) -> str:
        run = await self.workflow_service.get_or_404(session, job_id, user_id=user_id)
        self._ensure_chapter_rewrite_run(run)
        return await self.workflow_service.get_artifact_or_404(
            session,
            job_id,
            CHAPTER_REWRITE_ARTIFACT,
            user_id=user_id,
        )

    async def apply_artifact(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        user_id: str,
    ) -> ProjectChapter:
        run = await self.workflow_service.get_or_404(session, job_id, user_id=user_id)
        self._ensure_chapter_rewrite_run(run)
        if run.status != NOVEL_WORKFLOW_STATUS_SUCCEEDED:
            raise ConflictError("改写任务尚未成功完成，无法应用")
        if not run.project_id or not run.chapter_id:
            raise ConflictError("改写任务缺少目标章节")
        artifact = await self.workflow_service.get_artifact_or_404(
            session,
            job_id,
            CHAPTER_REWRITE_ARTIFACT,
            user_id=user_id,
        )
        if not artifact.strip():
            raise ConflictError("改写产物为空，无法应用")
        return await self.chapter_service.update(
            session,
            run.project_id,
            run.chapter_id,
            ProjectChapterUpdate(content=artifact),
            user_id=user_id,
        )

    @staticmethod
    def _ensure_chapter_rewrite_run(run: NovelWorkflowRun) -> None:
        if run.intent_type not in {
            CHAPTER_REWRITE_INTENT,
            IMPORTED_CHAPTER_FULL_REWRITE_INTENT,
        }:
            raise ConflictError("该任务不是章节改写任务")

    async def _adjacent_chapter_context(
        self,
        session: AsyncSession,
        chapter: ProjectChapter,
        *,
        project_origin: str,
    ) -> tuple[dict[str, str] | None, dict[str, str] | None]:
        if project_origin != "txt_import_rewrite":
            return None, None
        chapters = await self.chapter_repository.list_by_project(session, chapter.project_id)
        current_index = next(
            (index for index, item in enumerate(chapters) if item.id == chapter.id),
            -1,
        )
        if current_index < 0:
            return None, None
        previous = chapters[current_index - 1] if current_index > 0 else None
        next_chapter = chapters[current_index + 1] if current_index + 1 < len(chapters) else None
        return (
            self._chapter_context_payload(previous, boundary="tail"),
            self._chapter_context_payload(next_chapter, boundary="head"),
        )

    @staticmethod
    def _chapter_context_payload(
        chapter: ProjectChapter | None,
        *,
        boundary: str,
    ) -> dict[str, str] | None:
        if chapter is None:
            return None
        content = chapter.content or ""
        excerpt = (
            content[-_ADJACENT_CONTEXT_CHARS:]
            if boundary == "tail"
            else content[:_ADJACENT_CONTEXT_CHARS]
        )
        return {
            "id": chapter.id,
            "title": chapter.title,
            "summary": chapter.summary or "",
            "excerpt": excerpt.strip(),
        }
