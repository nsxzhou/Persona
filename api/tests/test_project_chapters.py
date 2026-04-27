from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient


OUTLINE_DETAIL = """## 第一幕：死局入门
> 从醒来到立住第一个生存目标

### 第1章：醒在死牢
- **核心事件**：沈砚醒来后发现自己成了即将秋后问斩的解元死囚

### 第2章：案卷上的名字
- **核心事件**：沈砚从狱卒口中得知卷宗里藏着另一个名字
"""


@pytest.mark.asyncio
async def test_sync_outline_creates_chapter_records_and_project_omits_content(
    initialized_client: AsyncClient,
    initialized_provider: dict[str, object],
) -> None:
    project_response = await initialized_client.post(
        "/api/v1/projects",
        json={
            "name": "天人请自重",
            "description": "",
            "status": "draft",
            "default_provider_id": initialized_provider["id"],
            "default_model": "",
            "style_profile_id": None,
        },
    )
    assert project_response.status_code == 201
    project = project_response.json()
    assert "content" not in project

    await initialized_client.patch(
        f"/api/v1/projects/{project['id']}/bible",
        json={"outline_detail": OUTLINE_DETAIL},
    )

    sync_response = await initialized_client.post(
        f"/api/v1/projects/{project['id']}/chapters/sync-outline"
    )
    assert sync_response.status_code == 200
    chapters = sync_response.json()

    assert [(c["volume_index"], c["chapter_index"], c["title"]) for c in chapters] == [
        (0, 0, "第1章：醒在死牢"),
        (0, 1, "第2章：案卷上的名字"),
    ]
    assert [c["word_count"] for c in chapters] == [0, 0]
    assert chapters[0]["memory_sync_status"] is None
    assert chapters[0]["memory_sync_proposed_state"] is None
    assert chapters[0]["memory_sync_proposed_threads"] is None

    list_response = await initialized_client.get(f"/api/v1/projects/{project['id']}/chapters")
    assert list_response.status_code == 200
    listed_chapters = list_response.json()
    assert [
        (
            c["id"],
            c["volume_index"],
            c["chapter_index"],
            c["title"],
            c["memory_sync_status"],
            c["memory_sync_proposed_state"],
            c["memory_sync_proposed_threads"],
        )
        for c in listed_chapters
    ] == [
        (
            c["id"],
            c["volume_index"],
            c["chapter_index"],
            c["title"],
            c["memory_sync_status"],
            c["memory_sync_proposed_state"],
            c["memory_sync_proposed_threads"],
        )
        for c in chapters
    ]


@pytest.mark.asyncio
async def test_can_update_only_owned_project_chapter(
    initialized_client: AsyncClient,
    initialized_provider: dict[str, object],
) -> None:
    project = (
        await initialized_client.post(
            "/api/v1/projects",
            json={
                "name": "章节权限测试",
                "description": "",
                "status": "draft",
                "default_provider_id": initialized_provider["id"],
                "default_model": "",
                "style_profile_id": None,
            },
        )
    ).json()
    await initialized_client.patch(
        f"/api/v1/projects/{project['id']}/bible",
        json={"outline_detail": OUTLINE_DETAIL},
    )
    chapters = (
        await initialized_client.post(f"/api/v1/projects/{project['id']}/chapters/sync-outline")
    ).json()
    chapter_id = chapters[0]["id"]

    update_response = await initialized_client.patch(
        f"/api/v1/projects/{project['id']}/chapters/{chapter_id}",
        json={"content": "沈砚睁开眼，潮湿霉味直往鼻腔里钻。"},
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["content"] == "沈砚睁开眼，潮湿霉味直往鼻腔里钻。"
    assert updated["word_count"] == len("沈砚睁开眼，潮湿霉味直往鼻腔里钻。")


@pytest.mark.asyncio
async def test_update_missing_chapter_returns_404(
    initialized_client: AsyncClient,
    initialized_provider: dict[str, object],
) -> None:
    project = (
        await initialized_client.post(
            "/api/v1/projects",
            json={
                "name": "章节不存在测试",
                "description": "",
                "status": "draft",
                "default_provider_id": initialized_provider["id"],
                "default_model": "",
                "style_profile_id": None,
            },
        )
    ).json()

    await initialized_client.patch(
        f"/api/v1/projects/{project['id']}/bible",
        json={"outline_detail": OUTLINE_DETAIL},
    )

    response = await initialized_client.patch(
        f"/api/v1/projects/{project['id']}/chapters/missing-chapter",
        json={"content": "不会保存"},
    )

    assert response.status_code == 404


def test_editor_prompt_builders_include_chapter_scoped_context() -> None:
    from app.prompts.beat import build_beat_generate_user_message
    from app.prompts.prose_writer import build_beat_expand_user_message

    beat_message = build_beat_generate_user_message(
        text_before_cursor="当前章光标前",
        outline_detail="总大纲",
        runtime_state="时间线",
        runtime_threads="伏笔",
        num_beats=5,
        current_chapter_context="第1章上下文",
        previous_chapter_context="前序章节摘要",
    )
    expand_message = build_beat_expand_user_message(
        text_before_cursor="当前章光标前",
        beat="主角发现案卷",
        beat_index=0,
        total_beats=5,
        preceding_beats_prose="",
        outline_detail="总大纲",
        runtime_state="时间线",
        runtime_threads="伏笔",
        current_chapter_context="第1章上下文",
        previous_chapter_context="前序章节摘要",
    )

    assert "## 前序章节" in beat_message
    assert "前序章节摘要" in beat_message
    assert "## 当前章节" in expand_message
    assert "第1章上下文" in expand_message
    assert "## 前序章节" in expand_message


@pytest.mark.asyncio
async def test_sync_outline_fetches_existing_chapters_once_and_reuses_in_memory_index() -> None:
    from app.services.project_chapters import ProjectChapterService

    repository = SimpleNamespace(
        list_by_project=AsyncMock(
            return_value=[
                SimpleNamespace(
                    id="chapter-1",
                    project_id="project-1",
                    volume_index=0,
                    chapter_index=0,
                    title="旧标题",
                    content="",
                    word_count=0,
                )
            ]
        ),
        get_by_position=AsyncMock(),
        create=AsyncMock(
            return_value=SimpleNamespace(
                id="chapter-2",
                project_id="project-1",
                volume_index=0,
                chapter_index=1,
                title="第2章：案卷上的名字",
                content="",
                word_count=0,
            )
        ),
        flush=AsyncMock(),
    )
    project_service = SimpleNamespace(
        get_or_404=AsyncMock(return_value=SimpleNamespace()),
        get_bible_or_404=AsyncMock(return_value=SimpleNamespace(outline_detail=OUTLINE_DETAIL)),
    )
    service = ProjectChapterService(repository=repository, project_service=project_service)

    chapters = await service.sync_outline(
        session=object(),
        project_id="project-1",
        user_id="user-1",
    )

    repository.list_by_project.assert_awaited_once()
    repository.get_by_position.assert_not_called()
    repository.create.assert_awaited_once()
    repository.flush.assert_awaited_once()
    assert chapters[0].title == "第1章：醒在死牢"


@pytest.mark.asyncio
async def test_update_invalidates_memory_sync_snapshot_when_saved_content_changes() -> None:
    from app.schemas.project_chapters import ProjectChapterUpdate
    from app.services.project_chapters import ProjectChapterService

    chapter = SimpleNamespace(
        id="chapter-1",
        project_id="project-1",
        volume_index=0,
        chapter_index=0,
        title="第1章：醒在死牢",
        content="旧正文",
        word_count=3,
        memory_sync_status="synced",
        memory_sync_source="auto",
        memory_sync_scope="generated_fragment",
        memory_sync_checked_at=datetime.now(UTC),
        memory_sync_checked_content_hash="old-hash",
        memory_sync_error_message=None,
        memory_sync_proposed_characters_status="旧角色快照",
        memory_sync_proposed_state="旧提议状态",
        memory_sync_proposed_threads="旧提议伏笔",
    )
    repository = SimpleNamespace(
        get_by_id=AsyncMock(return_value=chapter),
        flush=AsyncMock(),
    )
    project_service = SimpleNamespace(get_or_404=AsyncMock(return_value=SimpleNamespace()))
    service = ProjectChapterService(repository=repository, project_service=project_service)

    updated = await service.update(
        session=object(),
        project_id="project-1",
        chapter_id="chapter-1",
        payload=ProjectChapterUpdate(content="新的正文"),
        user_id="user-1",
    )

    assert updated.content == "新的正文"
    assert updated.memory_sync_status is None
    assert updated.memory_sync_source is None
    assert updated.memory_sync_scope is None
    assert updated.memory_sync_checked_at is None
    assert updated.memory_sync_checked_content_hash is None
    assert updated.memory_sync_error_message is None
    assert updated.memory_sync_proposed_characters_status is None
    assert updated.memory_sync_proposed_state is None
    assert updated.memory_sync_proposed_threads is None
    assert updated.memory_sync_proposed_summary is None


@pytest.mark.asyncio
async def test_update_keeps_memory_sync_snapshot_when_hash_matches_saved_content() -> None:
    from app.schemas.project_chapters import ProjectChapterUpdate
    from app.services.project_chapters import ProjectChapterService

    matching_hash = hashlib.sha256("新的正文".encode("utf-8")).hexdigest()
    chapter = SimpleNamespace(
        id="chapter-1",
        project_id="project-1",
        volume_index=0,
        chapter_index=0,
        title="第1章：醒在死牢",
        content="旧正文",
        word_count=3,
        memory_sync_status="no_change",
        memory_sync_source="manual",
        memory_sync_scope="chapter_full",
        memory_sync_checked_at=datetime.now(UTC),
        memory_sync_checked_content_hash=matching_hash,
        memory_sync_error_message=None,
        memory_sync_proposed_state=None,
        memory_sync_proposed_threads=None,
    )
    repository = SimpleNamespace(
        get_by_id=AsyncMock(return_value=chapter),
        flush=AsyncMock(),
    )
    project_service = SimpleNamespace(get_or_404=AsyncMock(return_value=SimpleNamespace()))
    service = ProjectChapterService(repository=repository, project_service=project_service)

    updated = await service.update(
        session=object(),
        project_id="project-1",
        chapter_id="chapter-1",
        payload=ProjectChapterUpdate(content="新的正文"),
        user_id="user-1",
    )

    assert updated.memory_sync_status == "no_change"
    assert updated.memory_sync_source == "manual"
    assert updated.memory_sync_scope == "chapter_full"
    assert updated.memory_sync_checked_content_hash == matching_hash
