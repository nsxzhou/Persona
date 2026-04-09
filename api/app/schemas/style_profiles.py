from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.style_analysis_jobs import (
    StyleDimensionSummary,
    StyleFewShotExample,
    StyleScenePrompts,
)


class StyleProfileCreate(BaseModel):
    job_id: str
    style_name: str = Field(min_length=1, max_length=120)
    analysis_summary: str = Field(min_length=1)
    global_system_prompt: str = Field(min_length=1)
    dimensions: StyleDimensionSummary
    scene_prompts: StyleScenePrompts
    few_shot_examples: list[StyleFewShotExample]


class StyleProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_job_id: str
    provider_id: str
    model_name: str
    source_filename: str
    style_name: str
    analysis_summary: str
    global_system_prompt: str
    dimensions: StyleDimensionSummary
    scene_prompts: StyleScenePrompts
    few_shot_examples: list[StyleFewShotExample]
    created_at: datetime
    updated_at: datetime

