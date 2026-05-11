from __future__ import annotations

from datetime import datetime
from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, RootModel

from app.schemas.novel_workflows import NovelWorkflowLogsResponse
from app.schemas.project_chapters import ProjectChapterResponse


CHAPTER_REWRITE_BATCH_STATUS_PENDING = "pending"
CHAPTER_REWRITE_BATCH_STATUS_RUNNING = "running"
CHAPTER_REWRITE_BATCH_STATUS_SUCCEEDED = "succeeded"
CHAPTER_REWRITE_BATCH_STATUS_FAILED = "failed"

CHAPTER_REWRITE_BATCH_ITEM_STATUS_WAITING = "waiting"
CHAPTER_REWRITE_BATCH_ITEM_STATUS_RUNNING = "running"
CHAPTER_REWRITE_BATCH_ITEM_STATUS_GENERATED = "generated"
CHAPTER_REWRITE_BATCH_ITEM_STATUS_FAILED = "failed"
CHAPTER_REWRITE_BATCH_ITEM_STATUS_APPLIED = "applied"

ChapterRewriteBatchStatus: TypeAlias = Literal["pending", "running", "succeeded", "failed"]
ChapterRewriteBatchItemStatus: TypeAlias = Literal[
    "waiting",
    "running",
    "generated",
    "failed",
    "applied",
]


class ChapterRewriteBatchCreateRequest(BaseModel):
    project_id: str
    chapter_ids: list[str] = Field(min_length=1)
    instruction: str = Field(min_length=1, max_length=4000)
    expansion_ratio_percent: int = Field(default=20, ge=1, le=100)


class ChapterRewriteBatchItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    batch_id: str
    chapter_id: str
    child_run_id: str | None
    position: int
    status: ChapterRewriteBatchItemStatus
    stage: str | None
    error_message: str | None
    applied_at: datetime | None
    chapter_title: str | None = None
    chapter: ProjectChapterResponse | None = None
    created_at: datetime
    updated_at: datetime


class ChapterRewriteBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    project_id: str
    instruction: str
    expansion_ratio_percent: int
    status: ChapterRewriteBatchStatus
    stage: str | None
    error_message: str | None
    total_count: int
    generated_count: int
    failed_count: int
    applied_count: int
    current_item_id: str | None = None
    current_chapter_id: str | None = None
    current_chapter_title: str | None = None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    items: list[ChapterRewriteBatchItemResponse] = Field(default_factory=list)


class ChapterRewriteBatchListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    instruction: str
    expansion_ratio_percent: int
    status: ChapterRewriteBatchStatus
    stage: str | None
    error_message: str | None
    total_count: int
    generated_count: int
    failed_count: int
    applied_count: int
    current_item_id: str | None = None
    current_chapter_id: str | None = None
    current_chapter_title: str | None = None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ChapterRewriteBatchMarkdownArtifactResponse(RootModel[str]):
    root: str = Field(min_length=0, description="Generated chapter rewrite preview.")


class ChapterRewriteBatchApplyItemResponse(BaseModel):
    item: ChapterRewriteBatchItemResponse
    chapter: ProjectChapterResponse


class ChapterRewriteBatchApplyResponse(BaseModel):
    applied: list[ChapterRewriteBatchApplyItemResponse]
    failed: list[ChapterRewriteBatchItemResponse] = Field(default_factory=list)


ChapterRewriteBatchItemLogsResponse = NovelWorkflowLogsResponse
