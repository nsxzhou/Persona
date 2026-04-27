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


class ConceptGenerateRequest(BaseModel):
    inspiration: str = Field(min_length=1, max_length=8000, description="用户灵感描述文本")
    provider_id: str = Field(description="AI 服务商 ID")
    model: str | None = Field(default=None, description="可选模型覆盖")
    generation_profile: GenerationProfile | None = None
    style_profile_id: str | None = Field(default=None, description="可选风格档案 ID")
    plot_profile_id: str | None = Field(default=None, description="可选情节档案 ID")
    count: int = Field(default=3, ge=1, le=5, description="生成候选数量")
    previous_output: str | None = Field(
        default=None,
        description="上一版生成结果，用于旧稿修订式重生成（可选）",
    )
    user_feedback: str | None = Field(
        default=None,
        description="用户本次对生成的意见/期望（可选），作为高优先级要求",
    )


class ConceptItem(BaseModel):
    title: str
    synopsis: str


class ConceptGenerateResponse(BaseModel):
    concepts: list[ConceptItem]
