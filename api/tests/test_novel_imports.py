from __future__ import annotations

import pytest
from httpx import AsyncClient


TXT_WITH_HEADINGS = """楔子

第1章 雨夜归来
雨声压着青石路。

第一章 旧案重开
沈砚翻开卷宗。
"""


@pytest.mark.asyncio
async def test_novel_import_preview_parses_numeric_and_chinese_headings(
    initialized_client: AsyncClient,
    initialized_provider: dict[str, object],
) -> None:
    response = await initialized_client.post(
        "/api/v1/novel-imports/preview",
        data={
            "project_name": "导入测试",
            "default_provider_id": initialized_provider["id"],
            "rights_confirmed": "true",
        },
        files={"file": ("novel.txt", TXT_WITH_HEADINGS.encode("utf-8"), "text/plain")},
    )

    assert response.status_code == 201
    preview = response.json()
    assert preview["project"]["project_name"] == "导入测试"
    assert preview["warnings"] == []
    assert [chapter["title"] for chapter in preview["chapters"]] == [
        "第1章 雨夜归来",
        "第一章 旧案重开",
    ]
    assert "楔子" in preview["chapters"][0]["content"]
    assert "第1章 雨夜归来" not in preview["chapters"][0]["content"]
    assert "第一章 旧案重开" not in preview["chapters"][1]["content"]
    assert preview["chapters"][0]["word_count"] == len(preview["chapters"][0]["content"])


@pytest.mark.asyncio
async def test_novel_import_preview_accepts_chinese_filename(
    initialized_client: AsyncClient,
    initialized_provider: dict[str, object],
) -> None:
    response = await initialized_client.post(
        "/api/v1/novel-imports/preview",
        data={
            "project_name": "中文文件名导入",
            "default_provider_id": initialized_provider["id"],
            "rights_confirmed": "true",
        },
        files={
            "file": (
                "反派：你也不想男主知道吧？.txt",
                TXT_WITH_HEADINGS.encode("utf-8"),
                "text/plain",
            )
        },
    )

    assert response.status_code == 201
    preview = response.json()
    assert preview["chapters"][0]["title"] == "第1章 雨夜归来"
    assert "第1章 雨夜归来" not in preview["chapters"][0]["content"]


@pytest.mark.asyncio
async def test_novel_import_preserves_full_heading_title_without_duplicating_content(
    initialized_client: AsyncClient,
    initialized_provider: dict[str, object],
) -> None:
    heading_title = "雨夜归来"
    response = await initialized_client.post(
        "/api/v1/novel-imports/preview",
        data={
            "project_name": "长标题导入",
            "default_provider_id": initialized_provider["id"],
            "rights_confirmed": "true",
        },
        files={
            "file": (
                "novel.txt",
                f"第1章 {heading_title}\n第二段正文。".encode("utf-8"),
                "text/plain",
            )
        },
    )

    assert response.status_code == 201
    chapter = response.json()["chapters"][0]
    assert chapter["title"] == f"第1章 {heading_title}"
    assert chapter["content"] == "第二段正文。"


@pytest.mark.asyncio
async def test_novel_import_no_heading_returns_single_chapter_warning(
    initialized_client: AsyncClient,
    initialized_provider: dict[str, object],
) -> None:
    response = await initialized_client.post(
        "/api/v1/novel-imports/preview",
        data={
            "project_name": "无标题导入",
            "default_provider_id": initialized_provider["id"],
            "rights_confirmed": "true",
        },
        files={"file": ("novel.txt", "只有一整段正文。".encode("utf-8"), "text/plain")},
    )

    assert response.status_code == 201
    preview = response.json()
    assert preview["warnings"] == ["no_standard_chapter_headings"]
    assert len(preview["chapters"]) == 1
    assert preview["chapters"][0]["content"] == "只有一整段正文。"


@pytest.mark.asyncio
async def test_novel_import_rejects_invalid_upload_cases(
    initialized_client: AsyncClient,
    initialized_provider: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_rights = await initialized_client.post(
        "/api/v1/novel-imports/preview",
        data={
            "project_name": "拒绝测试",
            "default_provider_id": initialized_provider["id"],
            "rights_confirmed": "false",
        },
        files={"file": ("novel.txt", b"content", "text/plain")},
    )
    assert missing_rights.status_code == 422

    non_txt = await initialized_client.post(
        "/api/v1/novel-imports/preview",
        data={
            "project_name": "拒绝测试",
            "default_provider_id": initialized_provider["id"],
            "rights_confirmed": "true",
        },
        files={"file": ("novel.pdf", b"content", "application/pdf")},
    )
    assert non_txt.status_code == 422

    empty = await initialized_client.post(
        "/api/v1/novel-imports/preview",
        data={
            "project_name": "拒绝测试",
            "default_provider_id": initialized_provider["id"],
            "rights_confirmed": "true",
        },
        files={"file": ("novel.txt", b"", "text/plain")},
    )
    assert empty.status_code == 422

    from app.core.config import get_settings

    monkeypatch.setenv("PERSONA_STYLE_ANALYSIS_MAX_UPLOAD_BYTES", "4")
    get_settings.cache_clear()
    oversized = await initialized_client.post(
        "/api/v1/novel-imports/preview",
        data={
            "project_name": "拒绝测试",
            "default_provider_id": initialized_provider["id"],
            "rights_confirmed": "true",
        },
        files={"file": ("novel.txt", b"too large", "text/plain")},
    )
    get_settings.cache_clear()
    assert oversized.status_code == 422


@pytest.mark.asyncio
async def test_novel_import_rejects_oversized_single_chapter(
    initialized_client: AsyncClient,
    initialized_provider: dict[str, object],
) -> None:
    response = await initialized_client.post(
        "/api/v1/novel-imports/preview",
        data={
            "project_name": "超长单章",
            "default_provider_id": initialized_provider["id"],
            "rights_confirmed": "true",
        },
        files={
            "file": (
                "novel.txt",
                ("正文" * 150_001).encode("utf-8"),
                "text/plain",
            )
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "单章内容过长，请拆分后再导入"


@pytest.mark.asyncio
async def test_novel_import_update_commit_creates_project_chapters_and_export(
    initialized_client: AsyncClient,
    initialized_provider: dict[str, object],
) -> None:
    preview_response = await initialized_client.post(
        "/api/v1/novel-imports/preview",
        data={
            "project_name": "导入后项目",
            "default_provider_id": initialized_provider["id"],
            "rights_confirmed": "true",
        },
        files={"file": ("novel.txt", TXT_WITH_HEADINGS.encode("utf-8"), "text/plain")},
    )
    assert preview_response.status_code == 201
    preview = preview_response.json()
    preview["chapters"][0]["title"] = "第1章 雨夜改题"
    preview["chapters"][0]["content"] = "改后的第一章正文"

    update_response = await initialized_client.patch(
        f"/api/v1/novel-imports/{preview['draft_id']}",
        json={"project": preview["project"], "chapters": preview["chapters"]},
    )
    assert update_response.status_code == 200
    updated_preview = update_response.json()
    assert updated_preview["chapters"][0]["word_count"] == len("改后的第一章正文")

    commit_response = await initialized_client.post(
        f"/api/v1/novel-imports/{preview['draft_id']}/commit"
    )
    assert commit_response.status_code == 200
    project_id = commit_response.json()["project_id"]
    project_response = await initialized_client.get(f"/api/v1/projects/{project_id}")
    assert project_response.status_code == 200
    assert project_response.json()["project_origin"] == "txt_import_rewrite"

    bible_response = await initialized_client.get(f"/api/v1/projects/{project_id}/bible")
    assert bible_response.status_code == 200
    outline_detail = bible_response.json()["outline_detail"]
    assert "## 第1卷 导入正文" in outline_detail
    assert "### 第 1 章 雨夜改题" in outline_detail
    assert "正文内容为准" in outline_detail
    assert "待补充" not in outline_detail

    chapters_response = await initialized_client.get(f"/api/v1/projects/{project_id}/chapters")
    assert chapters_response.status_code == 200
    chapters = chapters_response.json()
    assert [chapter["content"] for chapter in chapters] == [
        "改后的第一章正文",
        "沈砚翻开卷宗。",
    ]
    assert chapters[0]["word_count"] == len("改后的第一章正文")

    export_response = await initialized_client.get(
        f"/api/v1/projects/{project_id}/export?format=txt"
    )
    assert export_response.status_code == 200
    assert "改后的第一章正文" in export_response.text


@pytest.mark.asyncio
async def test_novel_import_draft_id_does_not_escape_storage(
    initialized_client: AsyncClient,
) -> None:
    response = await initialized_client.post(
        "/api/v1/novel-imports/not-a-uuid/commit"
    )

    assert response.status_code == 404
