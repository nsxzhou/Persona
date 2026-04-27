from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.provider_configs import ProviderSummary
from app.schemas.prompt_profiles import GenerationProfile


ProjectStatus = Literal["draft", "active", "paused"]
LengthPreset = Literal["short", "medium", "long"]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)
    status: ProjectStatus = "draft"
    default_provider_id: str
    default_model: str | None = None
    style_profile_id: str | None = None
    plot_profile_id: str | None = None
    generation_profile: GenerationProfile | None = None
    length_preset: LengthPreset = "short"
    auto_sync_memory: bool = False


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    status: ProjectStatus | None = None
    default_provider_id: str | None = None
    default_model: str | None = None
    style_profile_id: str | None = None
    plot_profile_id: str | None = None
    generation_profile: GenerationProfile | None = None
    length_preset: LengthPreset | None = None
    auto_sync_memory: bool | None = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    status: ProjectStatus
    default_provider_id: str
    default_model: str
    style_profile_id: str | None
    plot_profile_id: str | None
    generation_profile: GenerationProfile | None = None
    length_preset: str
    auto_sync_memory: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    provider: ProviderSummary


class ProjectBibleUpdate(BaseModel):
    inspiration: str | None = None
    world_building: str | None = None
    characters_blueprint: str | None = None
    outline_master: str | None = None
    outline_detail: str | None = None
    characters_status: str | None = None
    runtime_state: str | None = None
    runtime_threads: str | None = None
    story_summary: str | None = None


class ProjectBibleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    inspiration: str
    world_building: str
    characters_blueprint: str
    outline_master: str
    outline_detail: str
    characters_status: str
    runtime_state: str
    runtime_threads: str
    story_summary: str
    created_at: datetime
    updated_at: datetime


class ProjectSummaryResponse(BaseModel):
    """Lightweight project projection for list endpoints — excludes large Text fields."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    status: ProjectStatus
    default_provider_id: str
    default_model: str
    style_profile_id: str | None
    plot_profile_id: str | None
    generation_profile: GenerationProfile | None = None
    length_preset: str
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    provider: ProviderSummary
