from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import AsyncClient

from app.db.models import StyleAnalysisJob
from app.services.style_analysis_jobs import StyleAnalysisJobService


@pytest.mark.asyncio
async def test_create_style_analysis_job_persists_txt_and_exposes_job_endpoints(
    initialized_client: AsyncClient,
) -> None:
    provider_id = (await initialized_client.get("/api/v1/provider-configs")).json()[0]["id"]

    create_response = await initialized_client.post(
        "/api/v1/style-analysis-jobs",
        data={
            "style_name": "金庸武侠风",
            "provider_id": provider_id,
            "model": "gpt-4.1-mini",
        },
        files={"file": ("sample.txt", "第一章 风雪夜归人\n\n郭靖抬头望去。".encode("utf-8"), "text/plain")},
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["style_name"] == "金庸武侠风"
    assert created["status"] == "pending"
    assert created["stage"] is None
    assert created["error_message"] is None
    assert created["draft"] is None
    assert created["provider"]["id"] == provider_id
    assert created["sample_file"]["original_filename"] == "sample.txt"
    assert created["sample_file"]["byte_size"] > 0
    assert created["sample_file"]["character_count"] is None

    list_response = await initialized_client.get("/api/v1/style-analysis-jobs")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    detail_response = await initialized_client.get(f"/api/v1/style-analysis-jobs/{created['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == created["id"]


@pytest.mark.asyncio
async def test_create_style_analysis_job_rejects_non_txt_and_empty_file(
    initialized_client: AsyncClient,
) -> None:
    provider_id = (await initialized_client.get("/api/v1/provider-configs")).json()[0]["id"]

    invalid_type_response = await initialized_client.post(
        "/api/v1/style-analysis-jobs",
        data={"style_name": "错误文件", "provider_id": provider_id},
        files={"file": ("sample.md", "# not txt".encode("utf-8"), "text/markdown")},
    )
    assert invalid_type_response.status_code == 422
    assert invalid_type_response.json()["detail"] == "仅支持上传 .txt 样本文件"

    empty_file_response = await initialized_client.post(
        "/api/v1/style-analysis-jobs",
        data={"style_name": "空文件", "provider_id": provider_id},
        files={"file": ("sample.txt", b"", "text/plain")},
    )
    assert empty_file_response.status_code == 422
    assert empty_file_response.json()["detail"] == "上传的 TXT 文件为空"


@pytest.mark.asyncio
async def test_process_next_pending_job_generates_draft_and_updates_job_detail(
    initialized_client: AsyncClient,
    app_with_db: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_id = (await initialized_client.get("/api/v1/provider-configs")).json()[0]["id"]

    create_response = await initialized_client.post(
        "/api/v1/style-analysis-jobs",
        data={"style_name": "古龙风格实验", "provider_id": provider_id},
        files={"file": ("sample.txt", "夜色很冷。\n\n他忽然笑了。".encode("utf-8"), "text/plain")},
    )
    job_id = create_response.json()["id"]

    async def fake_generate_draft(self, *, job: StyleAnalysisJob, text: str) -> dict:
        assert job.id == job_id
        assert "夜色很冷" in text
        return {
            "style_name": job.style_name,
            "analysis_summary": "短句凌厉，转折快，留白重。",
            "global_system_prompt": "保留冷峻、克制和突兀转折。",
            "dimensions": {
                "vocabulary_habits": "高频使用冷、笑、忽然等简短动词和形容。",
                "syntax_rhythm": "短句为主，句间停顿明显。",
                "narrative_perspective": "第三人称贴近人物内心。",
                "dialogue_traits": "对白节制，往往带反讽。",
            },
            "scene_prompts": {
                "dialogue": "对白尽量短，带一点试探与反讽。",
                "action": "动作描写利落，不铺陈多余细节。",
                "environment": "环境描写偏冷色，服务情绪。",
            },
            "few_shot_examples": [
                {"type": "environment", "text": "夜色像一把薄刀，贴着窗纸划过去。"},
                {"type": "dialogue", "text": "他笑了笑，说这不算什么。"},
            ],
        }

    monkeypatch.setattr(StyleAnalysisJobService, "_generate_draft", fake_generate_draft)

    processed = await StyleAnalysisJobService().process_next_pending(app_with_db.state.session_factory)
    assert processed is True

    detail_response = await initialized_client.get(f"/api/v1/style-analysis-jobs/{job_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["status"] == "succeeded"
    assert detail["stage"] is None
    assert detail["error_message"] is None
    assert detail["sample_file"]["character_count"] == len("夜色很冷。\n\n他忽然笑了。")
    assert detail["draft"]["analysis_summary"] == "短句凌厉，转折快，留白重。"


@pytest.mark.asyncio
async def test_process_next_pending_job_records_failure_message(
    initialized_client: AsyncClient,
    app_with_db: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_id = (await initialized_client.get("/api/v1/provider-configs")).json()[0]["id"]

    create_response = await initialized_client.post(
        "/api/v1/style-analysis-jobs",
        data={"style_name": "失败任务", "provider_id": provider_id},
        files={"file": ("sample.txt", "大雨下了一夜。".encode("utf-8"), "text/plain")},
    )
    job_id = create_response.json()["id"]

    async def fake_generate_draft(self, *, job: StyleAnalysisJob, text: str) -> dict:
        del job, text
        raise RuntimeError("LLM 返回内容无法解析")

    monkeypatch.setattr(StyleAnalysisJobService, "_generate_draft", fake_generate_draft)

    processed = await StyleAnalysisJobService().process_next_pending(app_with_db.state.session_factory)
    assert processed is True

    detail_response = await initialized_client.get(f"/api/v1/style-analysis-jobs/{job_id}")
    detail = detail_response.json()
    assert detail["status"] == "failed"
    assert detail["error_message"] == "LLM 返回内容无法解析"
    assert detail["draft"] is None


@pytest.mark.asyncio
async def test_app_startup_marks_stale_running_jobs_failed(
    initialized_client: AsyncClient,
    app_with_db: FastAPI,
) -> None:
    provider_id = (await initialized_client.get("/api/v1/provider-configs")).json()[0]["id"]
    create_response = await initialized_client.post(
        "/api/v1/style-analysis-jobs",
        data={"style_name": "陈旧任务", "provider_id": provider_id},
        files={"file": ("sample.txt", "山风很急。".encode("utf-8"), "text/plain")},
    )
    job_id = create_response.json()["id"]

    async with app_with_db.state.session_factory() as session:
        job = await StyleAnalysisJobService().get_or_404(session, job_id)
        job.status = "running"
        job.stage = "analyzing"
        job.started_at = datetime.now(UTC) - timedelta(minutes=10)
        await session.commit()

    async with LifespanManager(app_with_db):
        pass

    detail_response = await initialized_client.get(f"/api/v1/style-analysis-jobs/{job_id}")
    detail = detail_response.json()
    assert detail["status"] == "failed"
    assert detail["error_message"] == "分析任务因服务重启中断，请重新提交"
