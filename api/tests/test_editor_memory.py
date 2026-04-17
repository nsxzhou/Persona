from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_memory_editor_service_marks_changed_when_threads_are_cleared() -> None:
    from app.schemas.editor import BibleUpdateRequest
    from app.services.editor import MemoryEditorService

    llm_service = SimpleNamespace(
        invoke_completion=AsyncMock(
            return_value="## 运行时状态\n\n旧状态\n\n## 伏笔与线索追踪\n\n"
        )
    )
    project_service = SimpleNamespace(
        get_or_404=AsyncMock(return_value=SimpleNamespace(provider=object()))
    )
    service = MemoryEditorService(
        llm_service=llm_service,
        project_service=project_service,
    )

    proposed_state, proposed_threads, changed = await service.propose_bible_update(
        session=object(),
        project_id="project-1",
        user_id="user-1",
        payload=BibleUpdateRequest(
            current_runtime_state="旧状态",
            current_runtime_threads="待清空伏笔",
            content_to_check="新正文",
            sync_scope="generated_fragment",
        ),
    )

    assert proposed_state == "旧状态"
    assert proposed_threads == ""
    assert changed is True


@pytest.mark.asyncio
async def test_memory_editor_service_marks_unchanged_when_both_sections_match() -> None:
    from app.schemas.editor import BibleUpdateRequest
    from app.services.editor import MemoryEditorService

    llm_service = SimpleNamespace(
        invoke_completion=AsyncMock(
            return_value="## 运行时状态\n\n旧状态\n\n## 伏笔与线索追踪\n\n旧伏笔"
        )
    )
    project_service = SimpleNamespace(
        get_or_404=AsyncMock(return_value=SimpleNamespace(provider=object()))
    )
    service = MemoryEditorService(
        llm_service=llm_service,
        project_service=project_service,
    )

    proposed_state, proposed_threads, changed = await service.propose_bible_update(
        session=object(),
        project_id="project-1",
        user_id="user-1",
        payload=BibleUpdateRequest(
            current_runtime_state="旧状态",
            current_runtime_threads="旧伏笔",
            content_to_check="新正文",
            sync_scope="generated_fragment",
        ),
    )

    assert proposed_state == "旧状态"
    assert proposed_threads == "旧伏笔"
    assert changed is False
