from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.provider_configs import ProviderSummary


class StyleDimensionSummary(BaseModel):
    vocabulary_habits: str = Field(min_length=1)
    syntax_rhythm: str = Field(min_length=1)
    narrative_perspective: str = Field(min_length=1)
    dialogue_traits: str = Field(min_length=1)


class StyleScenePrompts(BaseModel):
    dialogue: str = Field(min_length=1)
    action: str = Field(min_length=1)
    environment: str = Field(min_length=1)


class StyleFewShotExample(BaseModel):
    type: str = Field(min_length=1, max_length=32)
    text: str = Field(min_length=1)


class StyleDraft(BaseModel):
    style_name: str = Field(min_length=1, max_length=120)
    analysis_summary: str = Field(min_length=1)
    global_system_prompt: str = Field(min_length=1)
    dimensions: StyleDimensionSummary
    scene_prompts: StyleScenePrompts
    few_shot_examples: list[StyleFewShotExample]


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
    draft: StyleDraft | None = None

