from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProjectChapterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    volume_index: int
    chapter_index: int
    title: str
    content: str
    word_count: int
    created_at: datetime
    updated_at: datetime


class ProjectChapterUpdate(BaseModel):
    content: str = ""
