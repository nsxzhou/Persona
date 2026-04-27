from __future__ import annotations

from types import SimpleNamespace

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_novel_workflow_api_create_process_and_fetch_artifact(
    initialized_client: AsyncClient,
    initialized_provider: dict[str, object],
    app_with_db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.novel_workflow_pipeline import NovelWorkflowPipelineResult
    from app.services.novel_workflow_storage import NovelWorkflowStorageService
    from app.services.novel_workflow_worker import NovelWorkflowWorkerService

    project_response = await initialized_client.post(
        "/api/v1/projects",
        json={
            "name": "工作流测试项目",
            "description": "一个寒门书生被迫冒名顶替入局。",
            "status": "draft",
            "default_provider_id": initialized_provider["id"],
            "default_model": "",
        },
    )
    assert project_response.status_code == 201
    project = project_response.json()

    storage = NovelWorkflowStorageService()

    class FakePipeline:
        async def run(self, *, run_id: str, initial_state: dict[str, object]):
            markdown = "## 世界设定\n- 新的死牢秩序"
            await storage.write_stage_markdown_artifact(
                run_id,
                name="section_markdown",
                markdown=markdown,
            )
            return NovelWorkflowPipelineResult(
                persist_payload={"markdown": markdown},
                latest_artifacts=["section_markdown"],
            )

    async def fake_build_pipeline(self, **_):
        return FakePipeline()

    monkeypatch.setattr(
        NovelWorkflowWorkerService,
        "_build_pipeline",
        fake_build_pipeline,
    )

    create_response = await initialized_client.post(
        "/api/v1/novel-workflows",
        json={
            "intent_type": "section_generate",
            "project_id": project["id"],
            "section": "world_building",
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["status"] == "pending"
    assert created["intent_type"] == "section_generate"

    worker = NovelWorkflowWorkerService()
    processed = await worker.process_next_pending(app_with_db.state.session_factory)
    assert processed is True

    detail_response = await initialized_client.get(f"/api/v1/novel-workflows/{created['id']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["status"] == "succeeded"
    assert detail["latest_artifacts"] == ["section_markdown"]

    artifact_response = await initialized_client.get(
        f"/api/v1/novel-workflows/{created['id']}/artifacts/section_markdown"
    )
    assert artifact_response.status_code == 200
    assert artifact_response.json() == "## 世界设定\n- 新的死牢秩序"

    logs_response = await initialized_client.get(
        f"/api/v1/novel-workflows/{created['id']}/logs"
    )
    assert logs_response.status_code == 200
    assert "section_generate" in logs_response.json()["content"]


@pytest.mark.asyncio
async def test_novel_workflow_decision_endpoint_requeues_paused_run(
    initialized_client: AsyncClient,
    initialized_provider: dict[str, object],
    app_with_db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.novel_workflow_pipeline import (
        NovelWorkflowAwaitingHuman,
        NovelWorkflowPipelineResult,
    )
    from app.services.novel_workflow_storage import NovelWorkflowStorageService
    from app.services.novel_workflow_worker import NovelWorkflowWorkerService

    project_response = await initialized_client.post(
        "/api/v1/projects",
        json={
            "name": "章节工作流测试项目",
            "description": "一个寒门书生被迫冒名顶替入局。",
            "status": "draft",
            "default_provider_id": initialized_provider["id"],
            "default_model": "",
        },
    )
    assert project_response.status_code == 201
    project = project_response.json()

    storage = NovelWorkflowStorageService()
    call_count = {"count": 0}

    class FakePipeline:
        async def run(self, *, run_id: str, initial_state: dict[str, object]):
            call_count["count"] += 1
            if call_count["count"] == 1:
                await storage.write_stage_markdown_artifact(
                    run_id,
                    name="beats_markdown",
                    markdown="- beat 1\n- beat 2",
                )
                raise NovelWorkflowAwaitingHuman("beats")
            await storage.write_stage_markdown_artifact(
                run_id,
                name="prose_markdown",
                markdown="终稿正文",
            )
            return NovelWorkflowPipelineResult(
                persist_payload={
                    "chapter": {
                        "content": "终稿正文",
                        "beats_markdown": "- beat 1\n- beat 2",
                        "summary": "摘要",
                    },
                    "project_bible": {
                        "characters_status": "",
                        "runtime_state": "",
                        "runtime_threads": "",
                        "story_summary": "",
                    },
                },
                latest_artifacts=["beats_markdown", "prose_markdown"],
            )

    async def fake_build_pipeline(self, **_):
        return FakePipeline()

    monkeypatch.setattr(
        NovelWorkflowWorkerService,
        "_build_pipeline",
        fake_build_pipeline,
    )

    create_response = await initialized_client.post(
        "/api/v1/novel-workflows",
        json={
            "intent_type": "chapter_write",
            "project_id": project["id"],
            "current_chapter_context": "**第1章：醒在死牢**",
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()

    worker = NovelWorkflowWorkerService()
    processed = await worker.process_next_pending(app_with_db.state.session_factory)
    assert processed is True

    paused_status = await initialized_client.get(
        f"/api/v1/novel-workflows/{created['id']}/status"
    )
    assert paused_status.status_code == 200
    assert paused_status.json()["status"] == "paused"
    assert paused_status.json()["checkpoint_kind"] == "beats"

    decision_response = await initialized_client.post(
        f"/api/v1/novel-workflows/{created['id']}/decision",
        json={
            "action": "approve",
            "artifact_name": "beats_markdown",
        },
    )
    assert decision_response.status_code == 200
    assert decision_response.json()["status"] == "pending"

    processed = await worker.process_next_pending(app_with_db.state.session_factory)
    assert processed is True

    final_status = await initialized_client.get(
        f"/api/v1/novel-workflows/{created['id']}/status"
    )
    assert final_status.status_code == 200
    assert final_status.json()["status"] == "succeeded"
    assert "prose_markdown" in final_status.json()["latest_artifacts"]
