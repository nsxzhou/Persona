from __future__ import annotations

import pytest
from httpx import AsyncClient


OUTLINE_DETAIL = """## 第一卷

### 第1章 雨夜归来
- **核心事件**：主角在雨夜回城

### 第2章 旧案重开
- **核心事件**：旧案卷宗出现
"""


def test_chapter_rewrite_batch_worker_id_fits_locked_by_column() -> None:
    from app.db.models import ChapterRewriteBatch
    from app.services.chapter_rewrite_batch_worker import ChapterRewriteBatchWorkerService

    worker = ChapterRewriteBatchWorkerService()
    locked_by_length = ChapterRewriteBatch.__table__.c.locked_by.type.length

    assert locked_by_length is not None
    assert worker._worker_id.startswith("chapter-batch-worker-")
    assert len(worker._worker_id) <= locked_by_length


async def _create_project_with_chapters(
    client: AsyncClient,
    provider: dict[str, object],
) -> tuple[dict, list[dict]]:
    project = (
        await client.post(
            "/api/v1/projects",
            json={
                "name": "批量章节改写",
                "description": "",
                "status": "draft",
                "default_provider_id": provider["id"],
                "default_model": "",
            },
        )
    ).json()
    await client.patch(
        f"/api/v1/projects/{project['id']}/bible",
        json={"outline_detail": OUTLINE_DETAIL},
    )
    chapters = (
        await client.post(f"/api/v1/projects/{project['id']}/chapters/sync-outline")
    ).json()
    updated: list[dict] = []
    for index, chapter in enumerate(chapters, start=1):
        updated.append(
            (
                await client.patch(
                    f"/api/v1/projects/{project['id']}/chapters/{chapter['id']}",
                    json={"content": f"旧正文{index}"},
                )
            ).json()
        )
    return project, updated


@pytest.mark.asyncio
async def test_chapter_rewrite_batch_create_list_detail_logs_artifact_and_apply(
    initialized_client: AsyncClient,
    initialized_provider: dict[str, object],
    app_with_db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.chapter_rewrite_batch_worker import ChapterRewriteBatchWorkerService
    from app.services.novel_chapter_rewrite_jobs import CHAPTER_REWRITE_ARTIFACT
    from app.services.novel_workflow_pipeline import NovelWorkflowPipelineResult
    from app.services.novel_workflow_storage import NovelWorkflowStorageService
    from app.services.novel_workflow_worker import NovelWorkflowWorkerService

    project, chapters = await _create_project_with_chapters(initialized_client, initialized_provider)
    storage = NovelWorkflowStorageService()
    seen_chapters: list[str] = []

    class FakePipeline:
        async def run(self, *, run_id: str, initial_state: dict[str, object]):
            chapter = initial_state["chapter_snapshot"]
            assert isinstance(chapter, dict)
            seen_chapters.append(str(chapter["title"]))
            markdown = f"改写后：{chapter['title']}"
            await storage.append_job_log(run_id, f"生成 {chapter['title']}")
            await storage.write_stage_markdown_artifact(
                run_id,
                name=CHAPTER_REWRITE_ARTIFACT,
                markdown=markdown,
            )
            return NovelWorkflowPipelineResult(
                persist_payload={"markdown": markdown},
                latest_artifacts=[CHAPTER_REWRITE_ARTIFACT],
            )

    async def fake_build_pipeline(self, **_):
        return FakePipeline()

    monkeypatch.setattr(NovelWorkflowWorkerService, "_build_pipeline", fake_build_pipeline)

    create_response = await initialized_client.post(
        "/api/v1/chapter-rewrite-batches",
        json={
            "project_id": project["id"],
            "chapter_ids": [chapters[1]["id"], chapters[0]["id"]],
            "instruction": "增强场景张力",
        },
    )
    assert create_response.status_code == 201
    batch = create_response.json()
    assert batch["status"] == "pending"
    assert [item["chapter_id"] for item in batch["items"]] == [
        chapters[0]["id"],
        chapters[1]["id"],
    ]

    list_response = await initialized_client.get(
        f"/api/v1/chapter-rewrite-batches?project_id={project['id']}"
    )
    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == batch["id"]

    assert await ChapterRewriteBatchWorkerService().process_next_pending(
        app_with_db.state.session_factory
    ) is True
    assert seen_chapters == ["第1章 雨夜归来", "第2章 旧案重开"]

    detail_response = await initialized_client.get(
        f"/api/v1/chapter-rewrite-batches/{batch['id']}"
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["status"] == "succeeded"
    assert detail["generated_count"] == 2
    first_item = detail["items"][0]
    assert first_item["status"] == "generated"
    assert first_item["child_run_id"]

    logs_response = await initialized_client.get(
        f"/api/v1/chapter-rewrite-batches/{batch['id']}/items/{first_item['id']}/logs"
    )
    assert logs_response.status_code == 200
    assert "生成 第1章 雨夜归来" in logs_response.json()["content"]

    artifact_response = await initialized_client.get(
        f"/api/v1/chapter-rewrite-batches/{batch['id']}/items/{first_item['id']}/artifact"
    )
    assert artifact_response.status_code == 200
    assert artifact_response.json() == "改写后：第1章 雨夜归来"

    apply_item_response = await initialized_client.post(
        f"/api/v1/chapter-rewrite-batches/{batch['id']}/items/{first_item['id']}/apply"
    )
    assert apply_item_response.status_code == 200
    assert apply_item_response.json()["chapter"]["content"] == "改写后：第1章 雨夜归来"

    apply_batch_response = await initialized_client.post(
        f"/api/v1/chapter-rewrite-batches/{batch['id']}/apply"
    )
    assert apply_batch_response.status_code == 200
    assert len(apply_batch_response.json()["applied"]) == 1


@pytest.mark.asyncio
async def test_chapter_rewrite_batch_continues_after_item_failure_and_fails_when_all_fail(
    initialized_client: AsyncClient,
    initialized_provider: dict[str, object],
    app_with_db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.chapter_rewrite_batch_worker import ChapterRewriteBatchWorkerService
    from app.services.novel_chapter_rewrite_jobs import CHAPTER_REWRITE_ARTIFACT
    from app.services.novel_workflow_pipeline import NovelWorkflowPipelineResult
    from app.services.novel_workflow_storage import NovelWorkflowStorageService
    from app.services.novel_workflow_worker import NovelWorkflowWorkerService

    project, chapters = await _create_project_with_chapters(initialized_client, initialized_provider)
    storage = NovelWorkflowStorageService()
    fail_next = {"enabled": True}

    class FakePipeline:
        async def run(self, *, run_id: str, initial_state: dict[str, object]):
            chapter = initial_state["chapter_snapshot"]
            assert isinstance(chapter, dict)
            if fail_next["enabled"]:
                fail_next["enabled"] = False
                raise RuntimeError("provider failed")
            markdown = f"成功：{chapter['title']}"
            await storage.write_stage_markdown_artifact(
                run_id,
                name=CHAPTER_REWRITE_ARTIFACT,
                markdown=markdown,
            )
            return NovelWorkflowPipelineResult(
                persist_payload={"markdown": markdown},
                latest_artifacts=[CHAPTER_REWRITE_ARTIFACT],
            )

    async def fake_build_pipeline(self, **_):
        return FakePipeline()

    monkeypatch.setattr(NovelWorkflowWorkerService, "_build_pipeline", fake_build_pipeline)

    partial = (
        await initialized_client.post(
            "/api/v1/chapter-rewrite-batches",
            json={
                "project_id": project["id"],
                "chapter_ids": [chapter["id"] for chapter in chapters],
                "instruction": "批量改写",
            },
        )
    ).json()
    assert await ChapterRewriteBatchWorkerService().process_next_pending(
        app_with_db.state.session_factory
    ) is True
    partial_detail = (
        await initialized_client.get(f"/api/v1/chapter-rewrite-batches/{partial['id']}")
    ).json()
    assert partial_detail["status"] == "succeeded"
    assert partial_detail["generated_count"] == 1
    assert partial_detail["failed_count"] == 1
    assert [item["status"] for item in partial_detail["items"]] == ["failed", "generated"]

    fail_next["enabled"] = True
    one_chapter = (
        await initialized_client.post(
            "/api/v1/chapter-rewrite-batches",
            json={
                "project_id": project["id"],
                "chapter_ids": [chapters[0]["id"]],
                "instruction": "全部失败",
            },
        )
    ).json()
    assert await ChapterRewriteBatchWorkerService().process_next_pending(
        app_with_db.state.session_factory
    ) is True
    failed_detail = (
        await initialized_client.get(f"/api/v1/chapter-rewrite-batches/{one_chapter['id']}")
    ).json()
    assert failed_detail["status"] == "failed"
    assert failed_detail["generated_count"] == 0
    assert failed_detail["failed_count"] == 1


@pytest.mark.asyncio
async def test_chapter_rewrite_batch_permissions_and_apply_guard(
    initialized_client: AsyncClient,
    initialized_provider: dict[str, object],
) -> None:
    project, chapters = await _create_project_with_chapters(initialized_client, initialized_provider)
    batch = (
        await initialized_client.post(
            "/api/v1/chapter-rewrite-batches",
            json={
                "project_id": project["id"],
                "chapter_ids": [chapters[0]["id"]],
                "instruction": "改写",
            },
        )
    ).json()

    apply_response = await initialized_client.post(
        f"/api/v1/chapter-rewrite-batches/{batch['id']}/items/{batch['items'][0]['id']}/apply"
    )
    assert apply_response.status_code == 409

    missing_chapter_response = await initialized_client.post(
        "/api/v1/chapter-rewrite-batches",
        json={
            "project_id": project["id"],
            "chapter_ids": ["missing"],
            "instruction": "改写",
        },
    )
    assert missing_chapter_response.status_code == 404
