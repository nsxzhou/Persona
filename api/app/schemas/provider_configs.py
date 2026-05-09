from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProviderConfigCreate(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    base_url: str = Field(min_length=1, max_length=255)
    api_key: str = Field(min_length=4, max_length=512)
    default_model: str = Field(min_length=1, max_length=100)
    is_enabled: bool = True
    immersion_prompt_override_enabled: bool = False
    immersion_system_prompt_suffix: str = ""
    chat_test_system_prompt: str = ""


class ProviderConfigUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=100)
    base_url: str | None = Field(default=None, min_length=1, max_length=255)
    api_key: str | None = Field(default=None, min_length=4, max_length=512)
    default_model: str | None = Field(default=None, min_length=1, max_length=100)
    is_enabled: bool | None = None
    immersion_prompt_override_enabled: bool | None = None
    immersion_system_prompt_suffix: str | None = None
    chat_test_system_prompt: str | None = None

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
    immersion_prompt_override_enabled: bool
    immersion_system_prompt_suffix: str
    chat_test_system_prompt: str
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


class ProviderChatTestMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)

    @field_validator("content")
    @classmethod
    def validate_non_blank_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("消息内容不能为空")
        return value


class ProviderChatTestSentMessage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: Literal["system", "user", "assistant"]
    content: str


class ProviderChatTestRequest(BaseModel):
    system_prompt: str = Field(min_length=1)
    messages: list[ProviderChatTestMessage] = Field(min_length=1)
    temperature: float = Field(default=0.7, ge=0, le=2)

    @field_validator("system_prompt")
    @classmethod
    def validate_non_blank_system_prompt(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("System Prompt 不能为空")
        return value

    @model_validator(mode="after")
    def validate_latest_user_message(self) -> "ProviderChatTestRequest":
        if self.messages[-1].role != "user" or not self.messages[-1].content.strip():
            raise ValueError("最后一条消息必须是非空用户消息")
        return self


class ProviderChatTestResponse(BaseModel):
    reply: str
    sent_messages: list[ProviderChatTestSentMessage]
    provider_prompt_override_applied: bool
    temperature: float
