from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProviderConfigCreate(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    base_url: str = Field(min_length=1, max_length=255)
    api_key: str = Field(min_length=4, max_length=512)
    default_model: str = Field(min_length=1, max_length=100)
    is_enabled: bool = True


class ProviderConfigUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=100)
    base_url: str | None = Field(default=None, min_length=1, max_length=255)
    api_key: str | None = Field(default=None, min_length=4, max_length=512)
    default_model: str | None = Field(default=None, min_length=1, max_length=100)
    is_enabled: bool | None = None

    @field_validator("api_key", mode="before")
    @classmethod
    def normalize_empty_api_key(cls, value: str | None) -> str | None:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class ProviderConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    label: str
    base_url: str
    default_model: str
    api_key_hint: str
    is_enabled: bool
    last_test_status: str | None
    last_test_error: str | None
    last_tested_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ProviderSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    label: str
    base_url: str
    default_model: str
    is_enabled: bool


class ConnectionTestResponse(BaseModel):
    status: str
    message: str
