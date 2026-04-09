from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.provider_configs import ProviderSummary


class EvidenceSnippet(BaseModel):
    excerpt: str = Field(min_length=1)
    location: str = Field(min_length=1)


class ExecutiveSummary(BaseModel):
    summary: str = Field(min_length=1)
    representative_evidence: list[EvidenceSnippet]


class BasicAssessment(BaseModel):
    text_type: str = Field(min_length=1)
    multi_speaker: bool
    batch_mode: bool
    location_indexing: str = Field(min_length=1)
    noise_handling: str = Field(min_length=1)


class SectionFinding(BaseModel):
    label: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    frequency: str = Field(min_length=1)
    confidence: Literal["high", "medium", "low"]
    is_weak_judgment: bool = False
    evidence: list[EvidenceSnippet]


class AnalysisReportSection(BaseModel):
    section: str = Field(min_length=1)
    title: str = Field(min_length=1)
    overview: str = Field(min_length=1)
    findings: list[SectionFinding]


class AnalysisReport(BaseModel):
    executive_summary: ExecutiveSummary
    basic_assessment: BasicAssessment
    sections: list[AnalysisReportSection]
    appendix: str | None = None


class StyleSummarySceneStrategy(BaseModel):
    scene: str = Field(min_length=1)
    instruction: str = Field(min_length=1)


class StyleSummary(BaseModel):
    style_name: str = Field(min_length=1, max_length=120)
    style_positioning: str = Field(min_length=1)
    core_features: list[str]
    lexical_preferences: list[str]
    rhythm_profile: list[str]
    punctuation_profile: list[str]
    imagery_and_themes: list[str]
    scene_strategies: list[StyleSummarySceneStrategy]
    avoid_or_rare: list[str]
    generation_notes: list[str]


class StyleScenePrompts(BaseModel):
    dialogue: str = Field(min_length=1)
    action: str = Field(min_length=1)
    environment: str = Field(min_length=1)


class PromptPackStyleControls(BaseModel):
    tone: str = Field(min_length=1)
    rhythm: str = Field(min_length=1)
    evidence_anchor: str = Field(min_length=1)


class PromptPackFewShotSlot(BaseModel):
    label: str = Field(min_length=1)
    type: str = Field(min_length=1, max_length=32)
    text: str = Field(min_length=1)
    purpose: str = Field(min_length=1)


class PromptPack(BaseModel):
    system_prompt: str = Field(min_length=1)
    scene_prompts: StyleScenePrompts
    hard_constraints: list[str]
    style_controls: PromptPackStyleControls
    few_shot_slots: list[PromptPackFewShotSlot]


class AnalysisMeta(BaseModel):
    source_filename: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    text_type: str = Field(min_length=1)
    has_timestamps: bool
    has_speaker_labels: bool
    has_noise_markers: bool
    uses_batch_processing: bool
    location_indexing: str = Field(min_length=1)
    chunk_count: int = Field(ge=1)


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


class StyleAnalysisJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    style_name: str
    provider_id: str
    model_name: str
    status: str
    stage: str | None
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
