from __future__ import annotations

import pytest
from httpx import AsyncClient


OUTLINE_DETAIL = """## 第一卷

### 第1章 雨夜归来
- **核心事件**：主角在雨夜回城
- **情绪走向**：压抑到警觉
- **章末钩子**：旧案卷宗出现
"""


@pytest.mark.asyncio
async def test_chapter_rewrite_job_artifact_and_apply_updates_export(
    initialized_client: AsyncClient,
    initialized_provider: dict[str, object],
    app_with_db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.novel_chapter_rewrite_jobs import CHAPTER_REWRITE_ARTIFACT
    from app.services.novel_workflow_pipeline import NovelWorkflowPipelineResult
    from app.services.novel_workflow_storage import NovelWorkflowStorageService
    from app.services.novel_workflow_worker import NovelWorkflowWorkerService

    project = (
        await initialized_client.post(
            "/api/v1/projects",
            json={
                "name": "章节改写测试",
                "description": "",
                "status": "draft",
                "default_provider_id": initialized_provider["id"],
                "default_model": "",
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
    chapter = (
        await initialized_client.patch(
            f"/api/v1/projects/{project['id']}/chapters/{chapters[0]['id']}",
            json={"content": "旧正文"},
        )
    ).json()

    storage = NovelWorkflowStorageService()

    class FakePipeline:
        async def run(self, *, run_id: str, initial_state: dict[str, object]):
            assert initial_state["intent_type"] == "chapter_enrichment_rewrite"
            assert initial_state["chapter_snapshot"]["content"] == "旧正文"
            assert initial_state["expansion_ratio_percent"] == 35
            await storage.write_stage_markdown_artifact(
                run_id,
                name=CHAPTER_REWRITE_ARTIFACT,
                markdown="新正文",
            )
            return NovelWorkflowPipelineResult(
                persist_payload={"markdown": "新正文"},
                latest_artifacts=[CHAPTER_REWRITE_ARTIFACT],
            )

    async def fake_build_pipeline(self, **_):
        return FakePipeline()

    monkeypatch.setattr(NovelWorkflowWorkerService, "_build_pipeline", fake_build_pipeline)

    create_response = await initialized_client.post(
        "/api/v1/novel-chapter-rewrite-jobs",
        json={
            "project_id": project["id"],
            "chapter_id": chapter["id"],
            "instruction": "增强雨夜压迫感",
            "expansion_ratio_percent": 35,
        },
    )
    assert create_response.status_code == 201
    job = create_response.json()
    assert job["intent_type"] == "chapter_enrichment_rewrite"

    assert await NovelWorkflowWorkerService().process_next_pending(
        app_with_db.state.session_factory
    ) is True

    artifact_response = await initialized_client.get(
        f"/api/v1/novel-chapter-rewrite-jobs/{job['id']}/artifact"
    )
    assert artifact_response.status_code == 200
    assert artifact_response.json() == "新正文"

    before_apply = (
        await initialized_client.get(f"/api/v1/projects/{project['id']}/chapters")
    ).json()
    assert before_apply[0]["content"] == "旧正文"

    apply_response = await initialized_client.post(
        f"/api/v1/novel-chapter-rewrite-jobs/{job['id']}/apply"
    )
    assert apply_response.status_code == 200
    assert apply_response.json()["chapter"]["content"] == "新正文"
    assert apply_response.json()["chapter"]["word_count"] == len("新正文")

    export_response = await initialized_client.get(
        f"/api/v1/projects/{project['id']}/export?format=txt"
    )
    assert export_response.status_code == 200
    assert "新正文" in export_response.text


@pytest.mark.asyncio
async def test_imported_chapter_rewrite_job_uses_imported_full_rewrite_intent(
    initialized_client: AsyncClient,
    initialized_provider: dict[str, object],
    app_with_db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.novel_chapter_rewrite_jobs import CHAPTER_REWRITE_ARTIFACT
    from app.services.novel_workflow_pipeline import NovelWorkflowPipelineResult
    from app.services.novel_workflow_storage import NovelWorkflowStorageService
    from app.services.novel_workflow_worker import NovelWorkflowWorkerService

    preview_response = await initialized_client.post(
        "/api/v1/novel-imports/preview",
        data={
            "project_name": "导入改写测试",
            "default_provider_id": initialized_provider["id"],
            "rights_confirmed": "true",
        },
        files={
            "file": (
                "novel.txt",
                (
                    "第1章 雨夜归来\n上一章正文结尾。\n"
                    "第2章 旧案重开\n当前章正文需要改写。\n"
                    "第3章 新线索\n下一章正文开头。"
                ).encode("utf-8"),
                "text/plain",
            )
        },
    )
    assert preview_response.status_code == 201
    preview = preview_response.json()
    commit_response = await initialized_client.post(
        f"/api/v1/novel-imports/{preview['draft_id']}/commit"
    )
    project_id = commit_response.json()["project_id"]
    chapters = (
        await initialized_client.get(f"/api/v1/projects/{project_id}/chapters")
    ).json()

    storage = NovelWorkflowStorageService()

    class FakePipeline:
        async def run(self, *, run_id: str, initial_state: dict[str, object]):
            assert initial_state["intent_type"] == "imported_chapter_full_rewrite"
            assert initial_state["chapter_snapshot"]["content"] == "当前章正文需要改写。"
            assert initial_state["expansion_ratio_percent"] == 20
            assert initial_state["imported_previous_chapter"]["title"] == "第 1 章 雨夜归来"
            assert "上一章正文结尾" in initial_state["imported_previous_chapter"]["excerpt"]
            assert initial_state["imported_next_chapter"]["title"] == "第 3 章 新线索"
            assert "下一章正文开头" in initial_state["imported_next_chapter"]["excerpt"]
            await storage.write_stage_markdown_artifact(
                run_id,
                name=CHAPTER_REWRITE_ARTIFACT,
                markdown="导入改写后正文",
            )
            return NovelWorkflowPipelineResult(
                persist_payload={"markdown": "导入改写后正文"},
                latest_artifacts=[CHAPTER_REWRITE_ARTIFACT],
            )

    async def fake_build_pipeline(self, **_):
        return FakePipeline()

    monkeypatch.setattr(NovelWorkflowWorkerService, "_build_pipeline", fake_build_pipeline)

    create_response = await initialized_client.post(
        "/api/v1/novel-chapter-rewrite-jobs",
        json={
            "project_id": project_id,
            "chapter_id": chapters[1]["id"],
            "instruction": "润色当前章节",
        },
    )
    assert create_response.status_code == 201
    job = create_response.json()
    assert job["intent_type"] == "imported_chapter_full_rewrite"

    assert await NovelWorkflowWorkerService().process_next_pending(
        app_with_db.state.session_factory
    ) is True

    artifact_response = await initialized_client.get(
        f"/api/v1/novel-chapter-rewrite-jobs/{job['id']}/artifact"
    )
    assert artifact_response.status_code == 200
    assert artifact_response.json() == "导入改写后正文"


@pytest.mark.asyncio
async def test_direct_imported_chapter_rewrite_rejects_normal_project(
    initialized_client: AsyncClient,
    initialized_provider: dict[str, object],
) -> None:
    project = (
        await initialized_client.post(
            "/api/v1/projects",
            json={
                "name": "普通项目",
                "description": "",
                "status": "draft",
                "default_provider_id": initialized_provider["id"],
                "default_model": "",
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

    response = await initialized_client.post(
        "/api/v1/novel-workflows",
        json={
            "intent_type": "imported_chapter_full_rewrite",
            "project_id": project["id"],
            "chapter_id": chapters[0]["id"],
            "selected_text": "旧正文",
            "rewrite_instruction": "改写",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "导入章节改写仅支持 TXT 导入改写项目"


@pytest.mark.asyncio
async def test_chapter_rewrite_apply_requires_completed_job(
    initialized_client: AsyncClient,
    initialized_provider: dict[str, object],
) -> None:
    project = (
        await initialized_client.post(
            "/api/v1/projects",
            json={
                "name": "章节改写状态测试",
                "description": "",
                "status": "draft",
                "default_provider_id": initialized_provider["id"],
                "default_model": "",
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
    chapter = (
        await initialized_client.patch(
            f"/api/v1/projects/{project['id']}/chapters/{chapters[0]['id']}",
            json={"content": "旧正文"},
        )
    ).json()
    job = (
        await initialized_client.post(
            "/api/v1/novel-chapter-rewrite-jobs",
            json={
                "project_id": project["id"],
                "chapter_id": chapter["id"],
                "instruction": "增强压迫感",
            },
        )
    ).json()

    apply_response = await initialized_client.post(
        f"/api/v1/novel-chapter-rewrite-jobs/{job['id']}/apply"
    )
    assert apply_response.status_code == 409
