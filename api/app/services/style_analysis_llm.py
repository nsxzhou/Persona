from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.security import decrypt_secret
from app.db.models import ProviderConfig

StructuredOutputT = TypeVar("StructuredOutputT", bound=BaseModel)


class StructuredLLMClient:
    def __init__(
        self,
        *,
        model_factory: Callable[..., Any] = init_chat_model,
        secret_decrypter: Callable[[str], str] = decrypt_secret,
    ) -> None:
        self._model_factory = model_factory
        self._secret_decrypter = secret_decrypter

    def build_model(self, *, provider: ProviderConfig, model_name: str) -> Any:
        settings = get_settings()
        return self._model_factory(
            model=model_name,
            model_provider="openai",
            base_url=provider.base_url,
            api_key=self._secret_decrypter(provider.api_key_encrypted),
            temperature=0.0,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )

    async def ainvoke_structured(
        self,
        *,
        provider: ProviderConfig,
        model_name: str,
        schema: type[StructuredOutputT],
        prompt: str,
    ) -> StructuredOutputT:
        model = self.build_model(provider=provider, model_name=model_name)
        structured_model = model.with_structured_output(
            schema,
            method="json_schema",
            strict=True,
        )
        result = await structured_model.ainvoke([HumanMessage(content=prompt)])
        return schema.model_validate(result)
