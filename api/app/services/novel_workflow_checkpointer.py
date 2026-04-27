from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

from app.core.config import Settings, get_settings
from app.services.style_analysis_checkpointer import normalize_checkpoint_url


class NovelWorkflowCheckpointerFactory:
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
        raw_url = (settings.novel_workflow_checkpoint_url or settings.database_url).strip()
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

    async def delete_thread(self, run_id: str) -> None:
        try:
            checkpointer = await self.get()
            if hasattr(checkpointer, "adelete_thread"):
                await checkpointer.adelete_thread(run_id)
        except Exception:
            # cleanup failure should not break request/worker finalization
            return
