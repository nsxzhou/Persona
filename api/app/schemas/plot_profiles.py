from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.prompt_profiles import DesireOverlay, StoryEngineProfile

class PlotProfileCreate(BaseModel):
    job_id: str
    plot_name: str = Field(min_length=1, max_length=120)
    mount_project_id: str | None = None
    story_engine_markdown: str = Field(min_length=1)
    suggested_overlays: list[DesireOverlay] = Field(default_factory=list)
    plot_skeleton_markdown: str | None = None


class PlotProfileUpdate(BaseModel):
    plot_name: str = Field(min_length=1, max_length=120)
    mount_project_id: str | None = None
    story_engine_markdown: str = Field(min_length=1)
    suggested_overlays: list[DesireOverlay] = Field(default_factory=list)
    plot_skeleton_markdown: str | None = None


class PlotProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_job_id: str
    provider_id: str
    model_name: str
    source_filename: str
    plot_name: str
    analysis_report_markdown: str
    story_engine_payload: StoryEngineProfile
    story_engine_markdown: str
    suggested_overlays: list[DesireOverlay] = Field(default_factory=list)
    plot_skeleton_markdown: str | None = None
    created_at: datetime
    updated_at: datetime


class PlotProfileListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    provider_id: str
    model_name: str
    source_filename: str
    plot_name: str
    created_at: datetime
    updated_at: datetime
