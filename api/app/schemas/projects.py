from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.provider_configs import ProviderSummary

ProjectStatus = Literal["draft", "active", "paused"]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)
    status: ProjectStatus = "draft"
    default_provider_id: str
    default_model: str | None = None
    style_profile_id: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    status: ProjectStatus | None = None
    default_provider_id: str | None = None
    default_model: str | None = None
    style_profile_id: str | None = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    status: ProjectStatus
    default_provider_id: str
    default_model: str
    style_profile_id: str | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    provider: ProviderSummary

