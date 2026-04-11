from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Self, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.provider_configs import ProviderSummary


SECTION_TITLES: list[tuple[str, str]] = [
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

EXPECTED_SECTION_IDS = tuple(section for section, _title in SECTION_TITLES)


def validate_dossier_sections(sections: list["AnalysisReportSection"]) -> None:
    section_ids = tuple(section.section for section in sections)
    if section_ids != EXPECTED_SECTION_IDS:
        raise ValueError("sections must cover 3.1 through 3.12 exactly once and in order")


class EvidenceSnippet(BaseModel):
    excerpt: str = Field(
        min_length=1,
        description="Verbatim evidence excerpt copied from the analyzed sample text.",
    )
    location: str = Field(
        min_length=1,
        description="Timestamp, chapter, paragraph, or fallback location for the excerpt.",
    )


class ExecutiveSummary(BaseModel):
    summary: str = Field(min_length=1, description="Concise Chinese summary under 300 words.")
    representative_evidence: list[EvidenceSnippet] = Field(
        description="Representative excerpts that support the summary."
    )


class BasicAssessment(BaseModel):
    text_type: str = Field(min_length=1, description="Detected source text type.")
    multi_speaker: bool = Field(description="Whether the sample appears to contain multiple speakers.")
    batch_mode: bool = Field(description="Whether chunked batch analysis was used.")
    location_indexing: str = Field(min_length=1, description="How evidence locations are indexed.")
    noise_handling: str = Field(min_length=1, description="How timestamps, labels, or noise markers were handled.")


class SectionFinding(BaseModel):
    label: str = Field(min_length=1, description="Short label for this style feature.")
    summary: str = Field(min_length=1, description="Evidence-grounded explanation in simplified Chinese.")
    frequency: str = Field(min_length=1, description="Observed frequency or low-evidence note.")
    confidence: Literal["high", "medium", "low"] = Field(description="Confidence level supported by evidence.")
    is_weak_judgment: bool = Field(
        default=False,
        description="True when the conclusion is evidence-limited or inferential.",
    )
    evidence: list[EvidenceSnippet] = Field(description="Evidence excerpts supporting this finding.")


class AnalysisReportSection(BaseModel):
    section: str = Field(min_length=1, description="Dossier section id from 3.1 through 3.12.")
    title: str = Field(min_length=1, description="Chinese title for the dossier section.")
    overview: str = Field(min_length=1, description="Section-level overview.")
    findings: list[SectionFinding] = Field(description="Evidence-grounded findings for the section.")


class AnalysisReport(BaseModel):
    executive_summary: ExecutiveSummary = Field(description="Top-level summary and representative evidence.")
    basic_assessment: BasicAssessment = Field(description="Input classification and processing notes.")
    sections: list[AnalysisReportSection] = Field(description="Dossier sections 3.1 through 3.12 in order.")
    appendix: str | None = Field(default=None, description="Optional extra evidence index or caveats.")

    @model_validator(mode="after")
    def _validate_sections(self) -> Self:
        validate_dossier_sections(self.sections)
        return self


class ChunkAnalysis(BaseModel):
    chunk_index: int = Field(ge=0, description="Zero-based chunk index.")
    chunk_count: int = Field(ge=1, description="Total number of chunks in this analysis job.")
    sections: list[AnalysisReportSection] = Field(description="Chunk-local dossier sections 3.1 through 3.12.")

    @model_validator(mode="after")
    def _validate_sections(self) -> Self:
        validate_dossier_sections(self.sections)
        return self


class MergedAnalysis(BaseModel):
    classification: dict = Field(description="Input classification metadata used during the analysis.")
    sections: list[AnalysisReportSection] = Field(description="Merged dossier sections 3.1 through 3.12.")

    @model_validator(mode="after")
    def _validate_sections(self) -> Self:
        validate_dossier_sections(self.sections)
        return self


class StyleSummarySceneStrategy(BaseModel):
    scene: str = Field(min_length=1, description="Scene category such as dialogue, action, or environment.")
    instruction: str = Field(min_length=1, description="Actionable generation instruction for the scene.")


class StyleSummary(BaseModel):
    style_name: str = Field(min_length=1, max_length=120, description="Editable display name for the style.")
    style_positioning: str = Field(min_length=1, description="Compact positioning statement for the style.")
    core_features: list[str] = Field(description="Core style features backed by the analysis report.")
    lexical_preferences: list[str] = Field(description="Preferred words, phrases, and lexical patterns.")
    rhythm_profile: list[str] = Field(description="Sentence rhythm and paragraph cadence controls.")
    punctuation_profile: list[str] = Field(description="Punctuation habits to preserve or avoid.")
    imagery_and_themes: list[str] = Field(description="Recurring images, metaphors, and motifs.")
    scene_strategies: list[StyleSummarySceneStrategy] = Field(description="Scene-specific writing strategies.")
    avoid_or_rare: list[str] = Field(description="Patterns that are absent, rare, or should be avoided.")
    generation_notes: list[str] = Field(description="Practical notes for downstream generation.")


class StyleScenePrompts(BaseModel):
    dialogue: str = Field(min_length=1, description="Reusable prompt for dialogue scenes.")
    action: str = Field(min_length=1, description="Reusable prompt for action scenes.")
    environment: str = Field(min_length=1, description="Reusable prompt for environment scenes.")


class PromptPackStyleControls(BaseModel):
    tone: str = Field(min_length=1, description="Tone control for style generation.")
    rhythm: str = Field(min_length=1, description="Rhythm control for style generation.")
    evidence_anchor: str = Field(min_length=1, description="How generation should stay anchored to evidence.")


class PromptPackFewShotSlot(BaseModel):
    label: str = Field(min_length=1, description="Few-shot slot label.")
    type: str = Field(min_length=1, max_length=32, description="Few-shot category.")
    text: str = Field(min_length=1, description="Short illustrative sample text.")
    purpose: str = Field(min_length=1, description="Why this few-shot slot exists.")


class PromptPack(BaseModel):
    system_prompt: str = Field(min_length=1, description="Reusable global style system prompt.")
    scene_prompts: StyleScenePrompts = Field(description="Scene-specific reusable prompts.")
    hard_constraints: list[str] = Field(description="Non-negotiable style constraints.")
    style_controls: PromptPackStyleControls = Field(description="Compact controllable style knobs.")
    few_shot_slots: list[PromptPackFewShotSlot] = Field(description="Reusable few-shot placeholders.")


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
STYLE_ANALYSIS_JOB_STATUS_SUCCEEDED = "succeeded"
STYLE_ANALYSIS_JOB_STATUS_FAILED = "failed"

STYLE_ANALYSIS_JOB_STAGE_PREPARING_INPUT = "preparing_input"
STYLE_ANALYSIS_JOB_STAGE_ANALYZING_CHUNKS = "analyzing_chunks"
STYLE_ANALYSIS_JOB_STAGE_AGGREGATING = "aggregating"
STYLE_ANALYSIS_JOB_STAGE_REPORTING = "reporting"
STYLE_ANALYSIS_JOB_STAGE_SUMMARIZING = "summarizing"
STYLE_ANALYSIS_JOB_STAGE_COMPOSING_PROMPT_PACK = "composing_prompt_pack"

STYLE_ANALYSIS_JOB_STATUSES = (
    STYLE_ANALYSIS_JOB_STATUS_PENDING,
    STYLE_ANALYSIS_JOB_STATUS_RUNNING,
    STYLE_ANALYSIS_JOB_STATUS_SUCCEEDED,
    STYLE_ANALYSIS_JOB_STATUS_FAILED,
)

STYLE_ANALYSIS_JOB_STAGES = (
    STYLE_ANALYSIS_JOB_STAGE_PREPARING_INPUT,
    STYLE_ANALYSIS_JOB_STAGE_ANALYZING_CHUNKS,
    STYLE_ANALYSIS_JOB_STAGE_AGGREGATING,
    STYLE_ANALYSIS_JOB_STAGE_REPORTING,
    STYLE_ANALYSIS_JOB_STAGE_SUMMARIZING,
    STYLE_ANALYSIS_JOB_STAGE_COMPOSING_PROMPT_PACK,
)

StyleAnalysisJobStatus: TypeAlias = Literal[
    "pending",
    "running",
    "succeeded",
    "failed",
]
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
    analysis_report: AnalysisReport
    style_summary: StyleSummary
    prompt_pack: PromptPack
    created_at: datetime
    updated_at: datetime


class StyleAnalysisJobResponse(BaseModel):
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
    analysis_meta: AnalysisMeta | None = None
    analysis_report: AnalysisReport | None = None
    style_summary: StyleSummary | None = None
    prompt_pack: PromptPack | None = None
    style_profile: StyleProfileEmbeddedResponse | None = None


class StyleAnalysisJobStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: StyleAnalysisJobStatus
    stage: StyleAnalysisJobStage | None
    error_message: str | None
    updated_at: datetime


class StyleAnalysisJobListItemResponse(BaseModel):
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
