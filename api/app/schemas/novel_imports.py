from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.prompt_profiles import GenerationProfile, normalize_generation_profile_payload


NovelImportWarningCode = Literal["no_standard_chapter_headings"]


class NovelImportProjectMetadata(BaseModel):
    project_name: str = Field(min_length=1, max_length=120)
    default_provider_id: str
    default_model: str | None = Field(default=None, max_length=100)
    style_profile_id: str | None = None
    plot_profile_id: str | None = None
    generation_profile: GenerationProfile | None = None

    @field_validator("generation_profile", mode="before")
    @classmethod
    def normalize_generation_profile_request(cls, value: object) -> object:
        return normalize_generation_profile_payload(value)


class NovelImportChapterDraft(BaseModel):
    client_id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(default="", max_length=300_000)
    word_count: int = Field(default=0, ge=0)


class NovelImportDraftPreview(BaseModel):
    draft_id: str
    project: NovelImportProjectMetadata
    chapters: list[NovelImportChapterDraft] = Field(min_length=1, max_length=500)
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime
    expires_at: datetime


class NovelImportDraftUpdateRequest(BaseModel):
    project: NovelImportProjectMetadata
    chapters: list[NovelImportChapterDraft] = Field(min_length=1, max_length=500)


class NovelImportCommitResponse(BaseModel):
    project_id: str


class NovelImportDraftDocument(NovelImportDraftPreview):
    model_config = ConfigDict(extra="forbid")

    user_id: str
