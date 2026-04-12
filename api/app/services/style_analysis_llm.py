from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage

from app.core.config import get_settings
from app.core.security import decrypt_secret
from app.db.models import ProviderConfig


def _extract_text_content(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
                    continue
                if isinstance(text, dict):
                    value = text.get("value")
                    if isinstance(value, str):
                        parts.append(value)
                        continue
                if item.get("type") == "text" and isinstance(item.get("content"), str):
                    parts.append(item["content"])
        return "\n".join(part.strip() for part in parts if part and part.strip()).strip()
    return str(content).strip()


class MarkdownLLMClient:
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
        timeout_seconds = max(settings.llm_timeout_seconds, 60.0)
        return self._model_factory(
            model=model_name,
            model_provider="openai",
            base_url=provider.base_url,
            api_key=self._secret_decrypter(provider.api_key_encrypted),
            temperature=0.0,
            timeout=timeout_seconds,
            max_retries=settings.llm_max_retries,
        )

    async def ainvoke_markdown(
        self,
        *,
        model: Any,
        prompt: str,
    ) -> str:
        result = await model.ainvoke([HumanMessage(content=prompt)])
        text = _extract_text_content(getattr(result, "content", result))
        if not text:
            raise ValueError("LLM did not return markdown content")
        return text
