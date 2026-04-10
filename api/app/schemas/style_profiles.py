from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.style_analysis_jobs import AnalysisReport, PromptPack, StyleSummary


class StyleProfileCreate(BaseModel):
    job_id: str
    style_summary: StyleSummary
    prompt_pack: PromptPack


class StyleProfileUpdate(BaseModel):
    style_summary: StyleSummary
    prompt_pack: PromptPack


class StyleProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_job_id: str
    provider_id: str
    model_name: str
    source_filename: str
    style_name: str
    analysis_report: AnalysisReport
    style_summary: StyleSummary
    prompt_pack: PromptPack
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
