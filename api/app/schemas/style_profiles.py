from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.prompt_profiles import VoiceProfile

class StyleProfileCreate(BaseModel):
    job_id: str
    style_name: str = Field(min_length=1, max_length=120)
    mount_project_id: str | None = None
    voice_profile_markdown: str = Field(min_length=1)


class StyleProfileUpdate(BaseModel):
    style_name: str = Field(min_length=1, max_length=120)
    mount_project_id: str | None = None
    voice_profile_markdown: str = Field(min_length=1)


class StyleProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_job_id: str
    provider_id: str
    model_name: str
    source_filename: str
    style_name: str
    analysis_report_markdown: str
    voice_profile_payload: VoiceProfile
    voice_profile_markdown: str
    created_at: datetime
    updated_at: datetime


class StyleProfileListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    provider_id: str
    model_name: str
    source_filename: str
    style_name: str
    created_at: datetime
    updated_at: datetime
