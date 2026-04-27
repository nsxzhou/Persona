from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, RootModel

from app.schemas.prompt_profiles import GenerationProfile


NOVEL_WORKFLOW_STATUS_PENDING = "pending"
NOVEL_WORKFLOW_STATUS_RUNNING = "running"
NOVEL_WORKFLOW_STATUS_PAUSED = "paused"
NOVEL_WORKFLOW_STATUS_SUCCEEDED = "succeeded"
NOVEL_WORKFLOW_STATUS_FAILED = "failed"

NOVEL_WORKFLOW_STAGE_PREPARING = "preparing"
NOVEL_WORKFLOW_STAGE_GENERATING = "generating"
NOVEL_WORKFLOW_STAGE_WAITING_DECISION = "waiting_decision"
NOVEL_WORKFLOW_STAGE_PERSISTING = "persisting"
NOVEL_WORKFLOW_STAGE_POSTPROCESSING = "postprocessing"

NovelWorkflowStatus: TypeAlias = Literal["pending", "running", "paused", "succeeded", "failed"]
NovelWorkflowStage: TypeAlias = Literal[
    "preparing",
    "generating",
    "waiting_decision",
    "persisting",
    "postprocessing",
]
NovelWorkflowCheckpointKind: TypeAlias = Literal[
    "outline_bundle",
    "beats",
    "memory_update",
]
NovelWorkflowIntentType: TypeAlias = Literal[
    "concept_bootstrap",
    "project_bootstrap",
    "chapter_write",
    "memory_refresh",
    "section_generate",
    "volume_generate",
    "volume_chapters_generate",
    "continuation_write",
    "beats_generate",
    "beat_expand",
]


class MarkdownArtifactResponse(RootModel[str]):
    root: str = Field(min_length=0, description="Markdown artifact content.")


class NovelWorkflowLogsResponse(BaseModel):
    content: str = Field(description="Incremental log content from the requested offset.")
    next_offset: int = Field(ge=0, description="Next byte offset the client should request.")
    truncated: bool = Field(
        default=False,
        description="Whether the requested offset was reset because it exceeded the log length.",
    )


class NovelWorkflowModelOverrides(BaseModel):
    model_name: str | None = None
    enable_editor_pass: bool | None = None


class NovelWorkflowCreateRequest(BaseModel):
    intent_type: NovelWorkflowIntentType
    project_id: str | None = None
    chapter_id: str | None = None
    volume_index: int | None = Field(default=None, ge=0)
    section: str | None = None
    text_before_cursor: str = ""
    current_chapter_context: str = ""
    previous_chapter_context: str = ""
    total_content_length: int = Field(default=0, ge=0)
    beat: str | None = None
    beat_index: int | None = Field(default=None, ge=0)
    total_beats: int | None = Field(default=None, ge=1)
    preceding_beats_prose: str = ""
    content_to_check: str = ""
    sync_scope: Literal["generated_fragment", "chapter_full"] | None = None
    inspiration: str = ""
    count: int | None = Field(default=None, ge=1, le=5)
    provider_id: str | None = None
    model_name: str | None = None
    style_profile_id: str | None = None
    plot_profile_id: str | None = None
    generation_profile: GenerationProfile | None = None
    feedback: str | None = None
    previous_output: str | None = None
    model_overrides: NovelWorkflowModelOverrides | None = None


class NovelWorkflowDecisionRequest(BaseModel):
    action: Literal["approve", "revise"]
    artifact_name: str
    edited_markdown: str | None = None
    feedback: str | None = None


class NovelWorkflowBaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    intent_type: NovelWorkflowIntentType
    project_id: str | None
    chapter_id: str | None
    provider_id: str | None
    model_name: str | None
    status: NovelWorkflowStatus
    stage: NovelWorkflowStage | None
    checkpoint_kind: NovelWorkflowCheckpointKind | None = None
    latest_artifacts: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    pause_requested_at: datetime | None = None


class NovelWorkflowResponse(NovelWorkflowBaseResponse):
    request_payload: dict[str, Any]
    decision_payload: dict[str, Any] | None = None


class NovelWorkflowStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: NovelWorkflowStatus
    stage: NovelWorkflowStage | None
    checkpoint_kind: NovelWorkflowCheckpointKind | None = None
    latest_artifacts: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error_message: str | None
    updated_at: datetime
    pause_requested_at: datetime | None = None


NovelWorkflowListItemResponse = NovelWorkflowBaseResponse
