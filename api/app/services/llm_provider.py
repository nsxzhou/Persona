from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.redaction import summarize_exception
from app.db.models import ProviderConfig
from app.services.llm_model_factory import build_chat_model

logger = logging.getLogger(__name__)


class LLMProviderService:
    def _build_model(
        self,
        provider_config: ProviderConfig,
        *,
        temperature: float = 0.7,
        model_name: str | None = None,
    ):
        """Centralised helper that turns a ProviderConfig into a chat model.

        Must be called while the ORM session that loaded *provider_config*
        is still open, because it reads ORM attributes (base_url,
        api_key_encrypted, default_model) and decrypts the API key.
        """
        return build_chat_model(
            provider_config,
            model_name=model_name,
            temperature=temperature,
        )

    async def test_connection(self, provider_config: ProviderConfig) -> dict[str, str]:
        try:
            model = self._build_model(provider_config, temperature=0.0)
            await model.ainvoke([HumanMessage(content="Reply with OK")])
            return {"status": "success", "message": "连接成功"}
        except Exception as exc:
            logger.exception("provider connection test failed", extra={"provider_id": provider_config.id})
            return {
                "status": "error",
                "message": "Provider 连通性测试失败，请检查配置后重试",
                "error_summary": summarize_exception(exc),
            }

    async def stream_completion(
        self,
        provider_config: ProviderConfig,
        system_prompt: str,
        user_context: str,
    ) -> AsyncGenerator[str, None]:
        model = self._build_model(provider_config)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_context),
        ]
        async for chunk in model.astream(messages):
            if chunk.content:
                yield chunk.content

    async def stream_messages(
        self,
        provider_config: ProviderConfig,
        messages: list[Any],
    ) -> AsyncGenerator[str, None]:
        model = self._build_model(provider_config)
        async for chunk in model.astream(messages):
            if chunk.content:
                yield chunk.content

    async def invoke_completion(
        self,
        provider_config: ProviderConfig,
        system_prompt: str,
        user_context: str,
        model_name: str | None = None,
    ) -> str:
        """Non-streaming single LLM call; returns the full text."""
        model = self._build_model(provider_config, model_name=model_name)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_context),
        ]
        response = await model.ainvoke(messages)
        return str(response.content)
