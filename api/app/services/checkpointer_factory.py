from __future__ import annotations

import logging
from contextlib import AbstractAsyncContextManager
from typing import Any, ClassVar

from langgraph.checkpoint.memory import InMemorySaver

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


def normalize_checkpoint_url(raw_url: str) -> tuple[str, str] | None:
    if raw_url.startswith("sqlite+aiosqlite:///"):
        return ("sqlite", raw_url.removeprefix("sqlite+aiosqlite:///"))
    if raw_url.startswith("sqlite:///"):
        return ("sqlite", raw_url.removeprefix("sqlite:///"))
    if raw_url.startswith("postgresql+asyncpg://"):
        return ("postgres", "postgresql://" + raw_url.removeprefix("postgresql+asyncpg://"))
    if raw_url.startswith("postgresql://"):
        return ("postgres", raw_url)
    return None


class ConfiguredCheckpointerFactory:
    """Memoized LangGraph checkpointer factory with managed async lifecycle."""

    checkpoint_url_settings_name: ClassVar[str | None] = None
    delete_thread_failure_message: ClassVar[str | None] = None

    def __init__(self) -> None:
        self._checkpointer: Any | None = None
        self._context_manager: AbstractAsyncContextManager[Any] | None = None

    async def get(self) -> Any:
        if self._checkpointer is not None:
            return self._checkpointer

        settings = get_settings()
        checkpointer = await self._build_from_settings(settings)
        self._checkpointer = checkpointer
        return checkpointer

    async def aclose(self) -> None:
        if self._context_manager is not None:
            await self._context_manager.__aexit__(None, None, None)
            self._context_manager = None
        self._checkpointer = None

    async def _build_from_settings(self, settings: Settings) -> Any:
        raw_url = self._resolve_raw_url(settings)
        normalized = normalize_checkpoint_url(raw_url)
        if normalized is None:
            if "memory" in raw_url.lower():
                return InMemorySaver()
            raise ValueError(f"Unsupported database URL for checkpointer: {raw_url}")

        driver, conn_string = normalized
        if driver == "sqlite":
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

            self._context_manager = AsyncSqliteSaver.from_conn_string(conn_string)
            saver = await self._context_manager.__aenter__()
            await saver.setup()
            return saver

        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        self._context_manager = AsyncPostgresSaver.from_conn_string(conn_string)
        saver = await self._context_manager.__aenter__()
        await saver.setup()
        return saver

    def _resolve_raw_url(self, settings: Settings) -> str:
        configured_url = None
        if self.checkpoint_url_settings_name is not None:
            configured_url = getattr(settings, self.checkpoint_url_settings_name, None)
        return (configured_url or settings.database_url).strip()

    async def delete_thread(self, thread_id: str) -> None:
        try:
            checkpointer = await self.get()
            if hasattr(checkpointer, "adelete_thread"):
                await checkpointer.adelete_thread(thread_id)
        except Exception as exc:
            self._handle_delete_thread_failure(thread_id, exc)

    def _handle_delete_thread_failure(self, thread_id: str, exc: Exception) -> None:
        if self.delete_thread_failure_message is None:
            return
        logger.warning(self.delete_thread_failure_message, thread_id, exc)


class PlotAnalysisCheckpointerFactory(ConfiguredCheckpointerFactory):
    # Plot Lab intentionally shares Style Lab's checkpoint setting for now.
    checkpoint_url_settings_name = "style_analysis_checkpoint_url"
    delete_thread_failure_message = "Failed to delete checkpointer thread for job_id=%s: %s"


__all__ = [
    "ConfiguredCheckpointerFactory",
    "PlotAnalysisCheckpointerFactory",
    "normalize_checkpoint_url",
]
