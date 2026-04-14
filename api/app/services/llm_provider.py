from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import get_settings
from app.core.redaction import summarize_exception
from app.core.security import decrypt_secret
from app.db.models import ProviderConfig

logger = logging.getLogger(__name__)

CONNECTION_TEST_FAILED_MESSAGE = "Provider 连通性测试失败，请检查配置后重试"


class LLMProviderService:
    async def test_connection(self, provider_config: ProviderConfig) -> dict[str, str]:
        settings = get_settings()
        try:
            model = init_chat_model(
                model=provider_config.default_model,
                model_provider="openai",
                base_url=provider_config.base_url,
                api_key=decrypt_secret(provider_config.api_key_encrypted),
                temperature=0.0,
                timeout=settings.llm_timeout_seconds,
                max_retries=settings.llm_max_retries,
            )
            await model.ainvoke([HumanMessage(content="Reply with OK")])
            return {"status": "success", "message": "连接成功"}
        except Exception as exc:
            logger.exception("provider connection test failed", extra={"provider_id": provider_config.id})
            return {
                "status": "error",
                "message": CONNECTION_TEST_FAILED_MESSAGE,
                "error_summary": summarize_exception(exc),
            }

    async def stream_completion(
        self,
        provider_config: ProviderConfig,
        system_prompt: str,
        user_context: str,
    ) -> AsyncGenerator[str, None]:
        settings = get_settings()
        model = init_chat_model(
            model=provider_config.default_model,
            model_provider="openai",
            base_url=provider_config.base_url,
            api_key=decrypt_secret(provider_config.api_key_encrypted),
            temperature=0.7,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_context),
        ]
        async for chunk in model.astream(messages):
            if chunk.content:
                yield chunk.content
