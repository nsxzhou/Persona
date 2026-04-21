from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PlotProfileCreate(BaseModel):
    job_id: str
    plot_name: str = Field(min_length=1, max_length=120)
    mount_project_id: str | None = None
    plot_summary_markdown: str = Field(min_length=1)
    prompt_pack_markdown: str = Field(min_length=1)
    plot_skeleton_markdown: str | None = None


class PlotProfileUpdate(BaseModel):
    plot_name: str = Field(min_length=1, max_length=120)
    mount_project_id: str | None = None
    plot_summary_markdown: str = Field(min_length=1)
    prompt_pack_markdown: str = Field(min_length=1)
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
    plot_summary_markdown: str
    prompt_pack_markdown: str
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
