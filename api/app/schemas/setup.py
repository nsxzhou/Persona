from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.auth import UserResponse
from app.schemas.provider_configs import ProviderConfigCreate, ProviderConfigResponse


class SetupStatusResponse(BaseModel):
    initialized: bool


class SetupRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    provider: ProviderConfigCreate


class SetupResponse(BaseModel):
    user: UserResponse
    provider: ProviderConfigResponse

