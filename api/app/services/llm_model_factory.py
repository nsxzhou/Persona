from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain.chat_models import init_chat_model

from app.core.config import get_settings
from app.core.security import decrypt_secret
from app.db.models import ProviderConfig


def build_chat_model(
    provider_config: ProviderConfig,
    *,
    model_name: str | None = None,
    temperature: float = 0.7,
    model_factory: Callable[..., Any] | None = None,
    secret_decrypter: Callable[[str], str] | None = None,
) -> Any:
    resolved_model_factory = model_factory or init_chat_model
    resolved_secret_decrypter = secret_decrypter or decrypt_secret
    settings = get_settings()
    return resolved_model_factory(
        model=model_name or provider_config.default_model,
        model_provider="openai",
        base_url=provider_config.base_url,
        api_key=resolved_secret_decrypter(provider_config.api_key_encrypted),
        temperature=temperature,
        timeout=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
    )
