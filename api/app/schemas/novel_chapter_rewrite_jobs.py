from __future__ import annotations

from pydantic import BaseModel, Field, RootModel

from app.schemas.novel_workflows import (
    MarkdownArtifactResponse,
    NovelWorkflowBaseResponse,
    NovelWorkflowLogsResponse,
    NovelWorkflowStatusResponse,
)
from app.schemas.project_chapters import ProjectChapterResponse


class NovelChapterRewriteJobCreateRequest(BaseModel):
    project_id: str
    chapter_id: str
    instruction: str = Field(min_length=1, max_length=4000)
    expansion_ratio_percent: int = Field(default=20, ge=1, le=100)


class NovelChapterRewriteJobArtifactResponse(RootModel[str]):
    root: str = Field(min_length=0, description="Generated chapter rewrite preview.")


class NovelChapterRewriteJobApplyResponse(BaseModel):
    chapter: ProjectChapterResponse


NovelChapterRewriteJobResponse = NovelWorkflowBaseResponse
NovelChapterRewriteJobStatusResponse = NovelWorkflowStatusResponse
NovelChapterRewriteJobLogsResponse = NovelWorkflowLogsResponse
NovelChapterRewriteJobMarkdownArtifactResponse = MarkdownArtifactResponse
