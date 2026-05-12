from __future__ import annotations

from datetime import UTC, datetime, timedelta
from collections.abc import Callable
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.domain_errors import ConflictError, NotFoundError, UnprocessableEntityError
from app.db.models import ChapterRewriteBatch, ChapterRewriteBatchItem
from app.db.repositories.chapter_rewrite_batches import ChapterRewriteBatchRepository
from app.db.repositories.project_chapters import ProjectChapterRepository
from app.schemas.chapter_rewrite_batches import (
    CHAPTER_REWRITE_BATCH_ITEM_STATUS_APPLIED,
    CHAPTER_REWRITE_BATCH_ITEM_STATUS_FAILED,
    CHAPTER_REWRITE_BATCH_ITEM_STATUS_GENERATED,
    CHAPTER_REWRITE_BATCH_ITEM_STATUS_RUNNING,
    CHAPTER_REWRITE_BATCH_ITEM_STATUS_WAITING,
    CHAPTER_REWRITE_BATCH_STATUS_FAILED,
    CHAPTER_REWRITE_BATCH_STATUS_PENDING,
    CHAPTER_REWRITE_BATCH_STATUS_RUNNING,
    CHAPTER_REWRITE_BATCH_STATUS_SUCCEEDED,
    ChapterRewriteBatchApplyItemResponse,
    ChapterRewriteBatchApplyResponse,
    ChapterRewriteBatchCreateRequest,
)
from app.schemas.novel_chapter_rewrite_jobs import NovelChapterRewriteJobCreateRequest
from app.schemas.novel_workflows import (
    NOVEL_WORKFLOW_STATUS_FAILED,
    NOVEL_WORKFLOW_STATUS_SUCCEEDED,
)
from app.schemas.project_chapters import ProjectChapterResponse, ProjectChapterUpdate
from app.services.novel_chapter_rewrite_jobs import (
    CHAPTER_REWRITE_ARTIFACT,
    NovelChapterRewriteJobService,
)
from app.services.novel_workflows import NovelWorkflowService
from app.services.project_chapters import ProjectChapterService
from app.services.projects import ProjectService


class ChapterRewriteRunProcessor(Protocol):
    async def process_run_by_id(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        run_id: str,
    ) -> bool: ...

    async def aclose(self) -> None: ...


class ChapterRewriteBatchService:
    def __init__(
        self,
        *,
        repository: ChapterRewriteBatchRepository | None = None,
        project_service: ProjectService | None = None,
        chapter_service: ProjectChapterService | None = None,
        chapter_repository: ProjectChapterRepository | None = None,
        rewrite_job_service: NovelChapterRewriteJobService | None = None,
        workflow_service: NovelWorkflowService | None = None,
        run_processor_factory: Callable[[], ChapterRewriteRunProcessor] | None = None,
    ) -> None:
        self.repository = repository or ChapterRewriteBatchRepository()
        self.project_service = project_service or ProjectService()
        self.chapter_service = chapter_service or ProjectChapterService()
        self.chapter_repository = chapter_repository or ProjectChapterRepository()
        self.workflow_service = workflow_service or NovelWorkflowService()
        self.rewrite_job_service = rewrite_job_service or NovelChapterRewriteJobService(
            workflow_service=self.workflow_service,
            chapter_service=self.chapter_service,
        )
        self.run_processor_factory = run_processor_factory

    async def create(
        self,
        session: AsyncSession,
        payload: ChapterRewriteBatchCreateRequest,
        *,
        user_id: str,
    ) -> ChapterRewriteBatch:
        instruction = payload.instruction.strip()
        if not instruction:
            raise UnprocessableEntityError("请输入改写要求")
        await self.project_service.get_or_404(session, payload.project_id, user_id=user_id)
        requested = set(payload.chapter_ids)
        ordered_chapters = [
            chapter
            for chapter in await self.chapter_repository.list_by_project(session, payload.project_id)
            if chapter.id in requested
        ]
        if len(ordered_chapters) != len(requested):
            raise NotFoundError("章节不存在")
        batch = await self.repository.create(
            session,
            user_id=user_id,
            project_id=payload.project_id,
            instruction=instruction,
            expansion_ratio_percent=payload.expansion_ratio_percent,
            chapter_ids=[chapter.id for chapter in ordered_chapters],
            pending_status=CHAPTER_REWRITE_BATCH_STATUS_PENDING,
            item_waiting_status=CHAPTER_REWRITE_BATCH_ITEM_STATUS_WAITING,
        )
        return await self.get_or_404(session, batch.id, user_id=user_id)

    async def list(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        project_id: str | None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[ChapterRewriteBatch]:
        if project_id is not None:
            await self.project_service.get_or_404(session, project_id, user_id=user_id)
        return await self.repository.list(
            session,
            user_id=user_id,
            project_id=project_id,
            offset=offset,
            limit=min(max(limit, 1), 100),
        )

    async def get_or_404(
        self,
        session: AsyncSession,
        batch_id: str,
        *,
        user_id: str,
    ) -> ChapterRewriteBatch:
        batch = await self.repository.get_by_id(session, batch_id, user_id=user_id)
        if batch is None:
            raise NotFoundError("章节改写批次不存在")
        return batch

    async def get_item_or_404(
        self,
        session: AsyncSession,
        batch_id: str,
        item_id: str,
        *,
        user_id: str,
    ) -> ChapterRewriteBatchItem:
        item = await self.repository.get_item_by_id(
            session,
            batch_id,
            item_id,
            user_id=user_id,
        )
        if item is None:
            raise NotFoundError("章节改写条目不存在")
        return item

    async def get_item_logs_or_404(
        self,
        session: AsyncSession,
        batch_id: str,
        item_id: str,
        *,
        user_id: str,
        offset: int = 0,
    ):
        item = await self.get_item_or_404(session, batch_id, item_id, user_id=user_id)
        if item.child_run_id is None:
            raise NotFoundError("章节改写条目尚未开始")
        return await self.workflow_service.get_job_logs_or_404(
            session,
            item.child_run_id,
            user_id=user_id,
            offset=offset,
        )

    async def get_item_artifact_or_404(
        self,
        session: AsyncSession,
        batch_id: str,
        item_id: str,
        *,
        user_id: str,
    ) -> str:
        item = await self.get_item_or_404(session, batch_id, item_id, user_id=user_id)
        if item.status not in {
            CHAPTER_REWRITE_BATCH_ITEM_STATUS_GENERATED,
            CHAPTER_REWRITE_BATCH_ITEM_STATUS_APPLIED,
        }:
            raise ConflictError("章节改写条目尚未生成，无法查看产物")
        if item.child_run_id is None:
            raise NotFoundError("章节改写产物不存在")
        return await self.workflow_service.get_artifact_or_404(
            session,
            item.child_run_id,
            CHAPTER_REWRITE_ARTIFACT,
            user_id=user_id,
        )

    async def apply_item(
        self,
        session: AsyncSession,
        batch_id: str,
        item_id: str,
        *,
        user_id: str,
    ) -> ChapterRewriteBatchApplyItemResponse:
        batch = await self.get_or_404(session, batch_id, user_id=user_id)
        if batch.status not in {
            CHAPTER_REWRITE_BATCH_STATUS_SUCCEEDED,
            CHAPTER_REWRITE_BATCH_STATUS_FAILED,
        }:
            raise ConflictError("批量改写尚未完成，无法应用")
        item = next((candidate for candidate in batch.items if candidate.id == item_id), None)
        if item is None:
            raise NotFoundError("章节改写条目不存在")
        if item.status == CHAPTER_REWRITE_BATCH_ITEM_STATUS_APPLIED:
            raise ConflictError("章节改写条目已应用")
        if item.status != CHAPTER_REWRITE_BATCH_ITEM_STATUS_GENERATED:
            raise ConflictError("仅已生成的章节改写可以应用")
        if item.child_run_id is None:
            raise ConflictError("章节改写条目缺少工作流任务")
        artifact = await self.workflow_service.get_artifact_or_404(
            session,
            item.child_run_id,
            CHAPTER_REWRITE_ARTIFACT,
            user_id=user_id,
        )
        if not artifact.strip():
            raise ConflictError("改写产物为空，无法应用")
        chapter = await self.chapter_service.update(
            session,
            batch.project_id,
            item.chapter_id,
            ProjectChapterUpdate(content=artifact),
            user_id=user_id,
        )
        item.status = CHAPTER_REWRITE_BATCH_ITEM_STATUS_APPLIED
        item.applied_at = datetime.now(UTC)
        item.error_message = None
        batch.applied_count = self._count_items(
            batch.items,
            CHAPTER_REWRITE_BATCH_ITEM_STATUS_APPLIED,
        )
        await session.flush()
        return ChapterRewriteBatchApplyItemResponse(
            item=self._item_response(item),
            chapter=ProjectChapterResponse.model_validate(chapter),
        )

    async def apply_batch(
        self,
        session: AsyncSession,
        batch_id: str,
        *,
        user_id: str,
    ) -> ChapterRewriteBatchApplyResponse:
        batch = await self.get_or_404(session, batch_id, user_id=user_id)
        if batch.status not in {
            CHAPTER_REWRITE_BATCH_STATUS_SUCCEEDED,
            CHAPTER_REWRITE_BATCH_STATUS_FAILED,
        }:
            raise ConflictError("批量改写尚未完成，无法应用")
        applied: list[ChapterRewriteBatchApplyItemResponse] = []
        failed: list[ChapterRewriteBatchItem] = []
        for item in batch.items:
            if item.status != CHAPTER_REWRITE_BATCH_ITEM_STATUS_GENERATED:
                if item.status == CHAPTER_REWRITE_BATCH_ITEM_STATUS_FAILED:
                    failed.append(item)
                continue
            try:
                applied.append(await self.apply_item(session, batch_id, item.id, user_id=user_id))
            except ConflictError:
                failed.append(item)
        refreshed = await self.get_or_404(session, batch_id, user_id=user_id)
        failed_ids = {failed_item.id for failed_item in failed}
        return ChapterRewriteBatchApplyResponse(
            applied=applied,
            failed=[
                self._item_response(item)
                for item in refreshed.items
                if item.id in failed_ids
            ],
        )

    async def claim_next_pending_batch(
        self,
        session: AsyncSession,
        *,
        worker_id: str,
    ) -> str | None:
        return await self.repository.claim_pending_batch(
            session,
            worker_id=worker_id,
            pending_status=CHAPTER_REWRITE_BATCH_STATUS_PENDING,
            running_status=CHAPTER_REWRITE_BATCH_STATUS_RUNNING,
            now=datetime.now(UTC),
        )

    async def recover_stale_batches(
        self,
        session: AsyncSession,
        *,
        stale_after_seconds: int,
    ) -> None:
        await self.repository.recover_stale_batches(
            session,
            cutoff=datetime.now(UTC) - timedelta(seconds=stale_after_seconds),
            running_status=CHAPTER_REWRITE_BATCH_STATUS_RUNNING,
            failed_status=CHAPTER_REWRITE_BATCH_STATUS_FAILED,
            now=datetime.now(UTC),
        )

    async def process_claimed_batch(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        batch_id: str,
    ) -> None:
        async with session_factory() as session:
            batch = await self.repository.get_by_id(session, batch_id)
            if batch is None:
                return
            user_id = batch.user_id
            items = list(batch.items)

        if self.run_processor_factory is None:
            from app.services.novel_workflow_worker import NovelWorkflowWorkerService

            worker = NovelWorkflowWorkerService()
        else:
            worker = self.run_processor_factory()
        try:
            for item in items:
                run_id: str | None = None
                async with session_factory.begin() as session:
                    item = await self.repository.get_item_by_id(session, batch_id, item.id)
                    if item is None or item.status != CHAPTER_REWRITE_BATCH_ITEM_STATUS_WAITING:
                        continue
                    batch = item.batch
                    try:
                        batch.stage = "rewriting"
                        batch.last_heartbeat_at = datetime.now(UTC)
                        item.status = CHAPTER_REWRITE_BATCH_ITEM_STATUS_RUNNING
                        item.stage = "creating_workflow"
                        item.error_message = None
                        await session.flush()
                        run_id = await self._create_child_run(session, item, user_id=user_id)
                        item.child_run_id = run_id
                        item.stage = "running_workflow"
                        await session.flush()
                    except Exception as exc:
                        item.status = CHAPTER_REWRITE_BATCH_ITEM_STATUS_FAILED
                        item.stage = None
                        item.error_message = str(exc)
                        await self._refresh_batch_counts_from_db(session, batch)
                        await session.flush()
                        continue

                if run_id is None:
                    continue
                await worker.process_run_by_id(session_factory, run_id)

                async with session_factory.begin() as session:
                    item = await self.repository.get_item_by_id(session, batch_id, item.id)
                    if item is None:
                        continue
                    batch = item.batch
                    batch.last_heartbeat_at = datetime.now(UTC)
                    await self._sync_item_from_child_run(session, item, user_id=user_id)
                    await self._refresh_batch_counts_from_db(session, batch)
        finally:
            await worker.aclose()

        async with session_factory.begin() as session:
            batch = await self.repository.get_by_id(session, batch_id)
            if batch is None:
                return
            self._refresh_batch_counts(batch)
            batch.status = (
                CHAPTER_REWRITE_BATCH_STATUS_SUCCEEDED
                if batch.generated_count > 0
                else CHAPTER_REWRITE_BATCH_STATUS_FAILED
            )
            batch.stage = None
            if batch.status == CHAPTER_REWRITE_BATCH_STATUS_FAILED and not batch.error_message:
                batch.error_message = "所有章节改写均失败"
            batch.completed_at = datetime.now(UTC)
            batch.locked_by = None
            batch.locked_at = None
            batch.last_heartbeat_at = None
            await session.flush()

    async def _create_child_run(
        self,
        session: AsyncSession,
        item: ChapterRewriteBatchItem,
        *,
        user_id: str,
    ) -> str:
        run = await self.rewrite_job_service.create(
            session,
            NovelChapterRewriteJobCreateRequest(
                project_id=item.batch.project_id,
                chapter_id=item.chapter_id,
                instruction=item.batch.instruction,
                expansion_ratio_percent=item.batch.expansion_ratio_percent,
            ),
            user_id=user_id,
        )
        return run.id

    async def _sync_item_from_child_run(
        self,
        session: AsyncSession,
        item: ChapterRewriteBatchItem,
        *,
        user_id: str,
    ) -> None:
        if item.child_run_id is None:
            item.status = CHAPTER_REWRITE_BATCH_ITEM_STATUS_FAILED
            item.stage = None
            item.error_message = "章节改写条目缺少工作流任务"
            return
        run = await self.workflow_service.get_or_404(session, item.child_run_id, user_id=user_id)
        item.stage = run.stage
        if run.status == NOVEL_WORKFLOW_STATUS_SUCCEEDED:
            item.status = CHAPTER_REWRITE_BATCH_ITEM_STATUS_GENERATED
            item.stage = None
            item.error_message = None
        elif run.status == NOVEL_WORKFLOW_STATUS_FAILED:
            item.status = CHAPTER_REWRITE_BATCH_ITEM_STATUS_FAILED
            item.stage = None
            item.error_message = run.error_message or "章节改写失败"
        else:
            item.status = CHAPTER_REWRITE_BATCH_ITEM_STATUS_FAILED
            item.stage = None
            item.error_message = "章节改写工作流未完成"

    @staticmethod
    def enrich_batch(batch: ChapterRewriteBatch) -> ChapterRewriteBatch:
        current = next(
            (
                item
                for item in batch.items
                if item.status == CHAPTER_REWRITE_BATCH_ITEM_STATUS_RUNNING
            ),
            None,
        )
        if current is None:
            current = next(
                (
                    item
                    for item in batch.items
                    if item.status == CHAPTER_REWRITE_BATCH_ITEM_STATUS_WAITING
                ),
                None,
            )
        batch.current_item_id = current.id if current is not None else None
        batch.current_chapter_id = current.chapter_id if current is not None else None
        batch.current_chapter_title = current.chapter_title if current is not None else None
        return batch

    @staticmethod
    def _item_response(item: ChapterRewriteBatchItem):
        from app.schemas.chapter_rewrite_batches import ChapterRewriteBatchItemResponse

        return ChapterRewriteBatchItemResponse.model_validate(item)

    @staticmethod
    def _count_items(items: list[ChapterRewriteBatchItem], status: str) -> int:
        return sum(1 for item in items if item.status == status)

    def _refresh_batch_counts(self, batch: ChapterRewriteBatch) -> None:
        batch.generated_count = self._count_items(
            batch.items,
            CHAPTER_REWRITE_BATCH_ITEM_STATUS_GENERATED,
        ) + self._count_items(batch.items, CHAPTER_REWRITE_BATCH_ITEM_STATUS_APPLIED)
        batch.failed_count = self._count_items(
            batch.items,
            CHAPTER_REWRITE_BATCH_ITEM_STATUS_FAILED,
        )
        batch.applied_count = self._count_items(
            batch.items,
            CHAPTER_REWRITE_BATCH_ITEM_STATUS_APPLIED,
        )

    async def _refresh_batch_counts_from_db(
        self,
        session: AsyncSession,
        batch: ChapterRewriteBatch,
    ) -> None:
        result = await session.scalars(
            select(ChapterRewriteBatchItem.status).where(
                ChapterRewriteBatchItem.batch_id == batch.id
            )
        )
        statuses = list(result)
        batch.generated_count = statuses.count(
            CHAPTER_REWRITE_BATCH_ITEM_STATUS_GENERATED
        ) + statuses.count(CHAPTER_REWRITE_BATCH_ITEM_STATUS_APPLIED)
        batch.failed_count = statuses.count(CHAPTER_REWRITE_BATCH_ITEM_STATUS_FAILED)
        batch.applied_count = statuses.count(CHAPTER_REWRITE_BATCH_ITEM_STATUS_APPLIED)
