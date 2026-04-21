from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from openai import PermissionDeniedError
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage

from app.core.config import get_settings
from app.core.security import decrypt_secret
from app.db.models import ProviderConfig

logger = logging.getLogger(__name__)

_TEXT_RESPONSE_KEYS = ("content", "output_text", "text")
_EMPTY_RESPONSE_BACKOFF_SECONDS = (0.5, 1.0)
_TRANSIENT_PERMISSION_BACKOFF_SECONDS = (1.0, 2.0)


def _extract_from_mapping(mapping: dict) -> str:
    """Try the common text-bearing keys of a single dict; recurse one level."""
    for key in ("text", "output_text", "value", "content"):
        value = mapping.get(key)
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, dict):
            nested = value.get("value") or value.get("text") or value.get("content")
            if isinstance(nested, str):
                return nested.strip()
    return ""


def _extract_from_list(items: list) -> str:
    """Join text from a list of str/dict entries (as returned by some LLM providers)."""
    parts: list[str] = []
    for item in items:
        if isinstance(item, str):
            parts.append(item)
            continue
        if not isinstance(item, dict):
            continue
        text = _extract_from_mapping(item)
        if text:
            parts.append(text)
            continue
        if item.get("type") == "text" and isinstance(item.get("content"), str):
            parts.append(item["content"])
    return "\n".join(part.strip() for part in parts if part and part.strip()).strip()


def _extract_text_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, dict):
        return _extract_from_mapping(content)
    if isinstance(content, list):
        return _extract_from_list(content)
    return str(content).strip()


def _extract_text_from_mapping(mapping: Any, *, keys: tuple[str, ...]) -> tuple[str, str | None]:
    if not isinstance(mapping, dict):
        return "", None

    for key in keys:
        if key not in mapping:
            continue
        text = _extract_text_content(mapping.get(key))
        if text:
            return text, key
    return "", None


def _safe_mapping_keys(mapping: Any) -> list[str]:
    if not isinstance(mapping, dict):
        return []
    return sorted(str(key) for key in mapping.keys())


class EmptyMarkdownResponseError(ValueError):
    pass


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
        timeout_seconds = settings.llm_timeout_seconds
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
        total_attempts = max(
            len(_EMPTY_RESPONSE_BACKOFF_SECONDS),
            len(_TRANSIENT_PERMISSION_BACKOFF_SECONDS),
        ) + 1
        last_diagnostics: dict[str, Any] | None = None

        for attempt in range(1, total_attempts + 1):
            try:
                result = await model.ainvoke([HumanMessage(content=prompt)])
            except PermissionDeniedError as exc:
                if (
                    attempt < total_attempts
                    and self._is_retryable_permission_error(exc)
                    and attempt <= len(_TRANSIENT_PERMISSION_BACKOFF_SECONDS)
                ):
                    logger.warning(
                        "LLM gateway returned retryable permission error; retrying",
                        extra={
                            "attempt": attempt,
                            "total_attempts": total_attempts,
                            "error": str(exc),
                        },
                    )
                    await asyncio.sleep(_TRANSIENT_PERMISSION_BACKOFF_SECONDS[attempt - 1])
                    continue
                raise
            text, source, diagnostics = self._extract_markdown_text(result)
            last_diagnostics = diagnostics

            if text:
                if source == "additional_kwargs.reasoning_content":
                    logger.warning(
                        "Recovered markdown from reasoning_content fallback",
                        extra={
                            "source": source,
                            "finish_reason": diagnostics["finish_reason"],
                            "completion_tokens": diagnostics["completion_tokens"],
                        },
                    )
                elif source != "content":
                    logger.info(
                        "Recovered markdown from non-standard LLM field",
                        extra={
                            "source": source,
                            "finish_reason": diagnostics["finish_reason"],
                            "completion_tokens": diagnostics["completion_tokens"],
                        },
                    )
                return text

            if attempt < total_attempts:
                logger.warning(
                    "LLM returned empty markdown content; retrying",
                    extra={
                        "attempt": attempt,
                        "total_attempts": total_attempts,
                        "finish_reason": diagnostics["finish_reason"],
                        "completion_tokens": diagnostics["completion_tokens"],
                        "additional_keys": diagnostics["additional_keys"],
                        "response_metadata_keys": diagnostics["response_metadata_keys"],
                    },
                )
                await asyncio.sleep(_EMPTY_RESPONSE_BACKOFF_SECONDS[attempt - 1])

        assert last_diagnostics is not None
        message = self._build_empty_response_error_message(
            attempt=total_attempts,
            total_attempts=total_attempts,
            diagnostics=last_diagnostics,
        )
        logger.error(
            "LLM returned empty markdown content after retries exhausted",
            extra={
                "attempt": total_attempts,
                "total_attempts": total_attempts,
                "finish_reason": last_diagnostics["finish_reason"],
                "completion_tokens": last_diagnostics["completion_tokens"],
                "additional_keys": last_diagnostics["additional_keys"],
                "response_metadata_keys": last_diagnostics["response_metadata_keys"],
            },
        )
        raise EmptyMarkdownResponseError(message)

    def _is_retryable_permission_error(self, exc: PermissionDeniedError) -> bool:
        message = str(exc).lower()
        if "forbidden" in message:
            return True
        body = getattr(exc, "body", None)
        if isinstance(body, dict):
            error = body.get("error")
            if isinstance(error, dict):
                error_message = str(error.get("message", "")).lower()
                if "forbidden" in error_message:
                    return True
        return False

    def _extract_markdown_text(self, result: Any) -> tuple[str, str, dict[str, Any]]:
        additional_kwargs = getattr(result, "additional_kwargs", {}) or {}
        response_metadata = getattr(result, "response_metadata", {}) or {}

        candidates = [
            ("content", getattr(result, "content", result)),
        ]
        candidates.extend(
            (f"additional_kwargs.{key}", additional_kwargs.get(key)) for key in _TEXT_RESPONSE_KEYS
        )
        candidates.extend(
            (f"response_metadata.{key}", response_metadata.get(key)) for key in _TEXT_RESPONSE_KEYS
        )
        candidates.append(("additional_kwargs.reasoning_content", additional_kwargs.get("reasoning_content")))

        for source, candidate in candidates:
            text = _extract_text_content(candidate)
            if text:
                return text, source, self._build_response_diagnostics(
                    additional_kwargs=additional_kwargs,
                    response_metadata=response_metadata,
                )

        return "", "empty", self._build_response_diagnostics(
            additional_kwargs=additional_kwargs,
            response_metadata=response_metadata,
        )

    def _build_response_diagnostics(
        self,
        *,
        additional_kwargs: Any,
        response_metadata: Any,
    ) -> dict[str, Any]:
        token_usage = response_metadata.get("token_usage") if isinstance(response_metadata, dict) else {}
        completion_tokens = None
        if isinstance(token_usage, dict):
            completion_tokens = token_usage.get("completion_tokens")

        return {
            "finish_reason": response_metadata.get("finish_reason") if isinstance(response_metadata, dict) else None,
            "completion_tokens": completion_tokens,
            "additional_keys": _safe_mapping_keys(additional_kwargs),
            "response_metadata_keys": _safe_mapping_keys(response_metadata),
        }

    def _build_empty_response_error_message(
        self,
        *,
        attempt: int,
        total_attempts: int,
        diagnostics: dict[str, Any],
    ) -> str:
        return (
            "LLM did not return markdown content "
            f"(attempt={attempt}/{total_attempts}, "
            f"finish_reason={diagnostics['finish_reason']}, "
            f"completion_tokens={diagnostics['completion_tokens']}, "
            f"additional_keys={diagnostics['additional_keys']}, "
            f"response_metadata_keys={diagnostics['response_metadata_keys']})"
        )
