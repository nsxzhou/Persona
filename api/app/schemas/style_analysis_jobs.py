from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, RootModel

from app.schemas.provider_configs import ProviderSummary


STYLE_ANALYSIS_REPORT_SECTIONS: list[tuple[str, str]] = [
    ("3.1", "口头禅与常用表达"),
    ("3.2", "固定句式与节奏偏好"),
    ("3.3", "词汇选择偏好"),
    ("3.4", "句子构造习惯"),
    ("3.5", "生活经历线索"),
    ("3.6", "行业／地域词汇"),
    ("3.7", "自然化缺陷"),
    ("3.8", "写作忌口与避讳"),
    ("3.9", "比喻口味与意象库"),
    ("3.10", "思维模式与表达逻辑"),
    ("3.11", "常见场景的说话方式"),
    ("3.12", "个人价值取向与反复母题"),
]


class AnalysisReportMarkdown(RootModel[str]):
    root: str = Field(
        min_length=1,
        description="Markdown analysis report for Style Lab.",
    )


class StyleSummaryMarkdown(RootModel[str]):
    root: str = Field(
        min_length=1,
        description="Editable markdown style summary.",
    )


class PromptPackMarkdown(RootModel[str]):
    root: str = Field(
        min_length=1,
        description="Reusable markdown prompt pack.",
    )


class StyleAnalysisJobLogsResponse(BaseModel):
    content: str = Field(description="Incremental log content from the requested offset.")
    next_offset: int = Field(ge=0, description="Next byte offset the client should request.")
    truncated: bool = Field(
        default=False,
        description="Whether the requested offset was reset because it exceeded the log length.",
    )


class ChunkAnalysis(BaseModel):
    chunk_index: int = Field(ge=0, description="Zero-based chunk index.")
    chunk_count: int = Field(ge=1, description="Total number of chunks in this analysis job.")
    markdown: str = Field(min_length=1, description="Markdown chunk analysis.")


class MergedAnalysis(BaseModel):
    classification: dict[str, Any] = Field(description="Input classification metadata used during the analysis.")
    markdown: str = Field(min_length=1, description="Merged markdown analysis.")


class AnalysisMeta(BaseModel):
    source_filename: str = Field(min_length=1, description="Original uploaded TXT filename.")
    model_name: str = Field(min_length=1, description="LLM model used for analysis.")
    text_type: str = Field(min_length=1, description="Detected source text type.")
    has_timestamps: bool = Field(description="Whether timestamp markers were detected.")
    has_speaker_labels: bool = Field(description="Whether speaker labels were detected.")
    has_noise_markers: bool = Field(description="Whether bracketed/noise markers were detected.")
    uses_batch_processing: bool = Field(description="Whether chunked batch analysis was used.")
    location_indexing: str = Field(min_length=1, description="Evidence location indexing strategy.")
    chunk_count: int = Field(ge=1, description="Number of chunks analyzed.")


class StyleSampleFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    content_type: str | None
    byte_size: int
    character_count: int | None
    checksum_sha256: str
    created_at: datetime
    updated_at: datetime


STYLE_ANALYSIS_JOB_STATUS_PENDING = "pending"
STYLE_ANALYSIS_JOB_STATUS_RUNNING = "running"
STYLE_ANALYSIS_JOB_STATUS_PAUSED = "paused"
STYLE_ANALYSIS_JOB_STATUS_SUCCEEDED = "succeeded"
STYLE_ANALYSIS_JOB_STATUS_FAILED = "failed"

STYLE_ANALYSIS_JOB_STAGE_PREPARING_INPUT = "preparing_input"
STYLE_ANALYSIS_JOB_STAGE_ANALYZING_CHUNKS = "analyzing_chunks"
STYLE_ANALYSIS_JOB_STAGE_AGGREGATING = "aggregating"
STYLE_ANALYSIS_JOB_STAGE_REPORTING = "reporting"
STYLE_ANALYSIS_JOB_STAGE_SUMMARIZING = "summarizing"
STYLE_ANALYSIS_JOB_STAGE_COMPOSING_PROMPT_PACK = "composing_prompt_pack"

StyleAnalysisJobStatus: TypeAlias = Literal["pending", "running", "paused", "succeeded", "failed"]
StyleAnalysisJobStage: TypeAlias = Literal[
    "preparing_input",
    "analyzing_chunks",
    "aggregating",
    "reporting",
    "summarizing",
    "composing_prompt_pack",
]


class StyleProfileEmbeddedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_job_id: str
    provider_id: str
    model_name: str
    source_filename: str
    style_name: str
    created_at: datetime
    updated_at: datetime


class StyleAnalysisJobBaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    style_name: str
    provider_id: str
    model_name: str
    status: StyleAnalysisJobStatus
    stage: StyleAnalysisJobStage | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    provider: ProviderSummary
    sample_file: StyleSampleFileResponse
    style_profile_id: str | None = None
    pause_requested_at: datetime | None = None


class StyleAnalysisJobResponse(StyleAnalysisJobBaseResponse):
    style_profile: StyleProfileEmbeddedResponse | None = None


class StyleAnalysisJobStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: StyleAnalysisJobStatus
    stage: StyleAnalysisJobStage | None
    error_message: str | None
    updated_at: datetime
    pause_requested_at: datetime | None = None


class StyleAnalysisJobListItemResponse(StyleAnalysisJobBaseResponse):
    pass
