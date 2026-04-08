from __future__ import annotations

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage

from app.core.config import get_settings
from app.core.security import decrypt_secret
from app.db.models import ProviderConfig


class LLMProviderService:
    async def test_connection(self, provider_config: ProviderConfig) -> dict[str, str]:
        settings = get_settings()
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

