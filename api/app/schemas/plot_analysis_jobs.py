from __future__ import annotations

from datetime import datetime
from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, RootModel

from app.schemas.analysis_common import InputClassificationSchema
from app.schemas.prompt_profiles import PlotWritingGuideProfile
from app.schemas.provider_configs import ProviderSummary


PLOT_ANALYSIS_REPORT_SECTIONS: list[tuple[str, str]] = [
    ("3.1", "阶段划分与字数节奏"),
    ("3.2", "主爽点线与兑现节奏"),
    ("3.3", "冲突类型谱"),
    ("3.4", "主角道德与能力走向"),
    ("3.5", "关键角色引入模式"),
    ("3.6", "关系性质演变"),
    ("3.7", "爽点类型与兑现方式"),
    ("3.8", "章末钩子模式"),
    ("3.9", "反套路/颠覆点分布"),
    ("3.10", "道德灰度与下限"),
    ("3.11", "结局形状"),
    ("3.12", "标志性场景类型"),
]


class PlotAnalysisReportMarkdown(RootModel[str]):
    root: str = Field(
        min_length=1,
        description="Markdown analysis report for Plot Lab.",
    )


class PlotSkeletonMarkdown(RootModel[str]):
    root: str = Field(
        min_length=1,
        description="Markdown plot skeleton providing whole-book context for chunk analysis.",
    )


class StoryEngineMarkdown(RootModel[str]):
    root: str = Field(
        min_length=1,
        description="Reusable markdown plot writing guide.",
    )


class PlotAnalysisJobLogsResponse(BaseModel):
    content: str = Field(description="Incremental log content from the requested offset.")
    next_offset: int = Field(ge=0, description="Next byte offset the client should request.")
    truncated: bool = Field(
        default=False,
        description="Whether the requested offset was reset because it exceeded the log length.",
    )


class PlotChunkAnalysis(BaseModel):
    chunk_index: int = Field(ge=0, description="Zero-based chunk index.")
    chunk_count: int = Field(ge=1, description="Total number of chunks in this analysis job.")
    markdown: str = Field(min_length=1, description="Markdown chunk analysis.")


class PlotChunkSketch(BaseModel):
    """Compact plot ledger for one chunk, used to build sample-level plot reports."""

    chunk_index: int = Field(ge=0, description="Zero-based chunk index.")
    chunk_count: int = Field(ge=1, description="Total number of chunks in this analysis job.")
    characters_present: list[str] = Field(
        description="Names of characters present or mentioned in the chunk."
    )
    scene_units: list[str] = Field(description="Minimal scene units with place/actors/event/change.")
    main_events: list[str] = Field(description="Main-plot events directly supported by this chunk.")
    side_threads: list[str] = Field(description="Side-plot signals or secondary threads in this chunk.")
    payoff_points: list[str] = Field(description="Payoff, highlight, or reader-satisfaction points.")
    tension_points: list[str] = Field(description="Pressure, setback, abuse, threat, or pain points.")
    hooks: list[str] = Field(description="Chapter or scene hooks that create forward pull.")
    setup_payoff_links: list[str] = Field(description="Observed setup to payoff links inside this chunk.")
    pacing_shift: str = Field(description="Short description of the local pacing movement.")
    time_marker: Literal["linear", "flashback", "unclear"] = Field(
        description="Detected temporal ordering cue for this chunk."
    )
    sample_coverage: list[Literal[
        "opening_seen",
        "development_seen",
        "climax_seen",
        "ending_seen",
        "partial_fragment",
        "coverage_unclear",
    ]] = Field(description="Which story-stage signals are directly covered by this uploaded sample.")


class PlotMergedAnalysis(BaseModel):
    classification: InputClassificationSchema = Field(description="Input classification metadata used during the analysis.")
    markdown: str = Field(min_length=1, description="Merged markdown analysis.")


class PlotAnalysisMeta(BaseModel):
    source_filename: str = Field(min_length=1, description="Original uploaded TXT filename.")
    model_name: str = Field(min_length=1, description="LLM model used for analysis.")
    text_type: str = Field(min_length=1, description="Detected source text type.")
    has_timestamps: bool = Field(description="Whether timestamp markers were detected.")
    has_speaker_labels: bool = Field(description="Whether speaker labels were detected.")
    has_noise_markers: bool = Field(description="Whether bracketed/noise markers were detected.")
    uses_batch_processing: bool = Field(description="Whether chunked batch analysis was used.")
    location_indexing: str = Field(min_length=1, description="Evidence location indexing strategy.")
    chunk_count: int = Field(ge=1, description="Number of chunks analyzed.")


class PlotSampleFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    content_type: str | None
    byte_size: int
    character_count: int | None
    checksum_sha256: str
    created_at: datetime
    updated_at: datetime


PLOT_ANALYSIS_JOB_STATUS_PENDING = "pending"
PLOT_ANALYSIS_JOB_STATUS_RUNNING = "running"
PLOT_ANALYSIS_JOB_STATUS_PAUSED = "paused"
PLOT_ANALYSIS_JOB_STATUS_SUCCEEDED = "succeeded"
PLOT_ANALYSIS_JOB_STATUS_FAILED = "failed"

PLOT_ANALYSIS_JOB_STAGE_PREPARING_INPUT = "preparing_input"
PLOT_ANALYSIS_JOB_STAGE_BUILDING_SKELETON = "building_skeleton"
PLOT_ANALYSIS_JOB_STAGE_SELECTING_FOCUS_CHUNKS = "selecting_focus_chunks"
PLOT_ANALYSIS_JOB_STAGE_ANALYZING_FOCUS_CHUNKS = "analyzing_focus_chunks"
PLOT_ANALYSIS_JOB_STAGE_AGGREGATING = "aggregating"
PLOT_ANALYSIS_JOB_STAGE_REPORTING = "reporting"
PLOT_ANALYSIS_JOB_STAGE_POSTPROCESSING = "postprocessing"

PlotAnalysisJobStatus: TypeAlias = Literal["pending", "running", "paused", "succeeded", "failed"]
PlotAnalysisJobStage: TypeAlias = Literal[
    "preparing_input",
    "building_skeleton",
    "selecting_focus_chunks",
    "analyzing_focus_chunks",
    "aggregating",
    "reporting",
    "postprocessing",
]

class PlotProfileEmbeddedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_job_id: str
    provider_id: str
    model_name: str
    source_filename: str
    plot_name: str
    created_at: datetime
    updated_at: datetime


class PlotAnalysisJobBaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    plot_name: str
    provider_id: str
    model_name: str
    status: PlotAnalysisJobStatus
    stage: PlotAnalysisJobStage | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    provider: ProviderSummary
    sample_file: PlotSampleFileResponse
    plot_profile_id: str | None = None
    profile_plot_name: str | None = None
    pause_requested_at: datetime | None = None


class PlotAnalysisJobResponse(PlotAnalysisJobBaseResponse):
    plot_profile: PlotProfileEmbeddedResponse | None = None
    analysis_report_markdown: str | None = None
    plot_skeleton_markdown: str | None = None
    story_engine_payload: PlotWritingGuideProfile | None = None
    story_engine_markdown: str | None = None


class PlotAnalysisJobStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: PlotAnalysisJobStatus
    stage: PlotAnalysisJobStage | None
    error_message: str | None
    updated_at: datetime
    pause_requested_at: datetime | None = None


PlotAnalysisJobListItemResponse = PlotAnalysisJobBaseResponse
