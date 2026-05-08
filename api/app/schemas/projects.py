from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.provider_configs import ProviderSummary
from app.schemas.prompt_profiles import GenerationProfile


ProjectStatus = Literal["draft", "active", "paused"]
LengthPreset = Literal["short", "medium", "long"]
PromptAssetKind = Literal["character_card", "lorebook_entry", "author_note"]
PromptAssetScope = Literal["project", "chapter"]


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


class ProjectPromptAssetBase(BaseModel):
    kind: PromptAssetKind
    scope: PromptAssetScope = "project"
    chapter_id: str | None = None
    title: str = Field(min_length=1, max_length=160)
    content: str = Field(default="", max_length=20000)
    keywords: list[str] = Field(default_factory=list, max_length=32)
    enabled: bool = True
    always_on: bool = False
    priority: int = 0


class ProjectPromptAssetCreate(ProjectPromptAssetBase):
    pass


class ProjectPromptAssetUpdate(BaseModel):
    kind: PromptAssetKind | None = None
    scope: PromptAssetScope | None = None
    chapter_id: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=160)
    content: str | None = Field(default=None, max_length=20000)
    keywords: list[str] | None = Field(default=None, max_length=32)
    enabled: bool | None = None
    always_on: bool | None = None
    priority: int | None = None


class ProjectPromptAssetSuggestionPayload(ProjectPromptAssetBase):
    pass


class ProjectPromptAssetSuggestionChange(BaseModel):
    action: Literal["new", "update", "disable"]
    asset_id: str | None = None
    rationale: str = ""
    payload: ProjectPromptAssetSuggestionPayload | None = None


class PromptAssetInitSuggestionsResponse(BaseModel):
    changes: list[ProjectPromptAssetSuggestionChange] = Field(default_factory=list)


class ProjectPromptAssetApplySuggestionsRequest(BaseModel):
    changes: list[ProjectPromptAssetSuggestionChange] = Field(default_factory=list, max_length=64)


class ProjectPromptAssetApplySuggestionsResponse(BaseModel):
    assets: list["ProjectPromptAssetResponse"]


class ProjectPromptAssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    kind: PromptAssetKind
    scope: PromptAssetScope
    chapter_id: str | None
    title: str
    content: str
    keywords: list[str]
    enabled: bool
    always_on: bool
    priority: int
    created_at: datetime
    updated_at: datetime


class PromptStackPreviewRequest(BaseModel):
    chapter_id: str | None = None
    current_chapter_context: str = Field(default="", max_length=20000)
    text_before_cursor: str = Field(default="", max_length=40000)
    user_context: str = Field(default="", max_length=20000)


class PromptStackAssetManifestItem(BaseModel):
    id: str
    kind: PromptAssetKind
    scope: PromptAssetScope
    chapter_id: str | None
    title: str
    priority: int
    char_count: int
    original_char_count: int
    truncated: bool
    match_reasons: list[str]
    matched_keywords: list[str]


class PromptStackLayerManifestItem(BaseModel):
    key: str
    title: str
    char_count: int
    budget: int | None = None
    truncated: bool = False
    assets: list[PromptStackAssetManifestItem] = Field(default_factory=list)


class PromptStackManifest(BaseModel):
    layers: list[PromptStackLayerManifestItem]
    selected_assets: list[PromptStackAssetManifestItem]
    total_selected_assets: int
    final_prompt_char_count: int


class PromptStackPreviewResponse(BaseModel):
    prompt: str
    manifest: PromptStackManifest
