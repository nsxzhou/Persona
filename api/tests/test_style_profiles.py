from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.db.models import StyleAnalysisJob
from app.services.style_analysis_jobs import StyleAnalysisJobService


@pytest.mark.asyncio
async def test_create_style_profile_from_succeeded_job_and_mount_project(
    initialized_client: AsyncClient,
    app_with_db: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_id = (await initialized_client.get("/api/v1/provider-configs")).json()[0]["id"]

    project_response = await initialized_client.post(
        "/api/v1/projects",
        json={
            "name": "风格挂载项目",
            "description": "用于验证风格档案挂载",
            "status": "draft",
            "default_provider_id": provider_id,
            "default_model": "",
            "style_profile_id": None,
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    job_response = await initialized_client.post(
        "/api/v1/style-analysis-jobs",
        data={"style_name": "王家卫风格", "provider_id": provider_id},
        files={"file": ("sample.txt", "雨下得很慢，时间也很慢。".encode("utf-8"), "text/plain")},
    )
    job_id = job_response.json()["id"]

    async def fake_generate_draft(self, *, job: StyleAnalysisJob, text: str) -> dict:
        assert "雨下得很慢" in text
        return {
            "style_name": job.style_name,
            "analysis_summary": "节奏缓慢，情绪浓重，反复回望。",
            "global_system_prompt": "保留迟滞感、回忆感和都市孤独感。",
            "dimensions": {
                "vocabulary_habits": "偏爱时间、雨、灯、房间等意象。",
                "syntax_rhythm": "句子舒缓，常有重复和停顿。",
                "narrative_perspective": "第一人称或贴身第三人称回望过去。",
                "dialogue_traits": "对白克制，常有未说完的话。",
            },
            "scene_prompts": {
                "dialogue": "对白短促，带停顿和言外之意。",
                "action": "动作描写要轻，重点放在情绪余波。",
                "environment": "环境要有潮湿、霓虹和室内空气感。",
            },
            "few_shot_examples": [
                {"type": "environment", "text": "楼道里有一盏旧灯，亮了又暗。"},
                {"type": "dialogue", "text": "她说再见的时候，像是在说别的事。"},
            ],
        }

    monkeypatch.setattr(StyleAnalysisJobService, "_generate_draft", fake_generate_draft)
    processed = await StyleAnalysisJobService().process_next_pending(app_with_db.state.session_factory)
    assert processed is True

    create_profile_response = await initialized_client.post(
        "/api/v1/style-profiles",
        json={
            "job_id": job_id,
            "style_name": "王家卫风格（修订版）",
            "analysis_summary": "节奏缓慢，情绪浓重，反复回望。",
            "global_system_prompt": "保留迟滞感、回忆感和都市孤独感。",
            "dimensions": {
                "vocabulary_habits": "偏爱时间、雨、灯、房间等意象。",
                "syntax_rhythm": "句子舒缓，常有重复和停顿。",
                "narrative_perspective": "第一人称或贴身第三人称回望过去。",
                "dialogue_traits": "对白克制，常有未说完的话。",
            },
            "scene_prompts": {
                "dialogue": "对白短促，带停顿和言外之意。",
                "action": "动作描写要轻，重点放在情绪余波。",
                "environment": "环境要有潮湿、霓虹和室内空气感。",
            },
            "few_shot_examples": [
                {"type": "environment", "text": "楼道里有一盏旧灯，亮了又暗。"},
                {"type": "dialogue", "text": "她说再见的时候，像是在说别的事。"},
            ],
        },
    )

    assert create_profile_response.status_code == 201
    profile = create_profile_response.json()
    assert profile["style_name"] == "王家卫风格（修订版）"
    assert profile["source_job_id"] == job_id
    assert profile["provider_id"] == provider_id
    assert profile["source_filename"] == "sample.txt"

    list_profiles_response = await initialized_client.get("/api/v1/style-profiles")
    assert list_profiles_response.status_code == 200
    assert len(list_profiles_response.json()) == 1

    detail_response = await initialized_client.get(f"/api/v1/style-profiles/{profile['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == profile["id"]

    mount_response = await initialized_client.patch(
        f"/api/v1/projects/{project_id}",
        json={"style_profile_id": profile["id"]},
    )
    assert mount_response.status_code == 200
    assert mount_response.json()["style_profile_id"] == profile["id"]

