from __future__ import annotations

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
            "outline_detail": OUTLINE_DETAIL,
        },
    )
    assert project_response.status_code == 201
    project = project_response.json()
    assert "content" not in project

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

    list_response = await initialized_client.get(f"/api/v1/projects/{project['id']}/chapters")
    assert list_response.status_code == 200
    assert list_response.json() == chapters


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
                "outline_detail": OUTLINE_DETAIL,
            },
        )
    ).json()
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
                "outline_detail": OUTLINE_DETAIL,
            },
        )
    ).json()

    response = await initialized_client.patch(
        f"/api/v1/projects/{project['id']}/chapters/missing-chapter",
        json={"content": "不会保存"},
    )

    assert response.status_code == 404


def test_editor_prompt_builders_include_chapter_scoped_context() -> None:
    from app.services.editor_prompts import (
        build_beat_expand_user_message,
        build_beat_generate_user_message,
    )

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
