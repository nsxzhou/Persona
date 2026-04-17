from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

MemorySyncStatus = Literal["checking", "pending_review", "synced", "no_change", "failed"]
MemorySyncSource = Literal["auto", "manual"]
MemorySyncScope = Literal["generated_fragment", "chapter_full"]


class ProjectChapterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    volume_index: int
    chapter_index: int
    title: str
    content: str
    word_count: int
    memory_sync_status: MemorySyncStatus | None = None
    memory_sync_source: MemorySyncSource | None = None
    memory_sync_scope: MemorySyncScope | None = None
    memory_sync_checked_at: datetime | None = None
    memory_sync_checked_content_hash: str | None = None
    memory_sync_error_message: str | None = None
    memory_sync_proposed_state: str | None = None
    memory_sync_proposed_threads: str | None = None
    created_at: datetime
    updated_at: datetime


class ProjectChapterUpdate(BaseModel):
    content: str | None = None
    memory_sync_status: MemorySyncStatus | None = None
    memory_sync_source: MemorySyncSource | None = None
    memory_sync_scope: MemorySyncScope | None = None
    memory_sync_checked_at: datetime | None = None
    memory_sync_checked_content_hash: str | None = None
    memory_sync_error_message: str | None = None
    memory_sync_proposed_state: str | None = None
    memory_sync_proposed_threads: str | None = None
