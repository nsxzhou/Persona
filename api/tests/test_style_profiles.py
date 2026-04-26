from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select

from app.api.assemblers import build_style_profile_response_payload
from app.db.models import Project, StyleProfile
from app.services.style_analysis_jobs import StyleAnalysisJobService


def build_fake_analysis_report() -> str:
    return "# 执行摘要\n整体文风缓慢、潮湿、情绪延迟。\n"


def build_fake_voice_profile() -> str:
    return (
        "# Voice Profile\n"
        "## 3.1 口头禅与常用表达\n- 执行规则：短句推进，反问收束。\n\n"
        "## 3.2 固定句式与节奏偏好\n- 执行规则：长短句交替。\n\n"
        "## 3.3 词汇选择偏好\n- 执行规则：混用现代术语与古典四字格。\n\n"
        "## 3.4 句子构造习惯\n- 执行规则：句首落判断。\n\n"
        "## 3.5 生活经历线索\n- 执行规则：生活线索弱。\n\n"
        "## 3.6 行业／地域词汇\n- 执行规则：行业词偏运营。\n\n"
        "## 3.7 自然化缺陷\n- 执行规则：保留省略和跳接。\n\n"
        "## 3.8 写作忌口与避讳\n- 执行规则：少写解释性开场。\n\n"
        "## 3.9 比喻口味与意象库\n- 执行规则：意象偏月色与视线。\n\n"
        "## 3.10 思维模式与表达逻辑\n- 执行规则：观察、质疑、类比、结论递进。\n\n"
        "## 3.11 常见场景的说话方式\n- 执行规则：对白抢拍试探。\n\n"
        "## 3.12 个人价值取向与反复母题\n- 执行规则：强调效率和掌控。\n"
    )


@pytest.mark.asyncio
async def test_create_and_update_style_profile_from_succeeded_job_and_mount_project(
    initialized_client: AsyncClient,
    app_with_db: FastAPI,
    initialized_provider: dict[str, object],
) -> None:
    provider_id = str(initialized_provider["id"])

    project_response = await initialized_client.post(
        "/api/v1/projects",
        json={
            "name": "风格挂载项目",
            "description": "用于验证风格档案挂载",
            "status": "draft",
            "default_provider_id": provider_id,
            "default_model": "",
            "style_profile_id": None,
            "plot_profile_id": None,
            "generation_profile": None,
        },
    )
    project_id = project_response.json()["id"]

    create_job_response = await initialized_client.post(
        "/api/v1/style-analysis-jobs",
        data={"style_name": "王家卫风格", "provider_id": provider_id},
        files={"file": ("sample.txt", "第一章 风雪夜归人".encode("utf-8"), "text/plain")},
    )
    job_id = create_job_response.json()["id"]

    async with app_with_db.state.session_factory() as session:
        await StyleAnalysisJobService().mark_job_succeeded(
            session,
            job_id,
            analysis_meta_payload={
                "source_filename": "sample.txt",
                "model_name": str(initialized_provider["default_model"]),
                "text_type": "章节正文",
                "has_timestamps": False,
                "has_speaker_labels": False,
                "has_noise_markers": False,
                "uses_batch_processing": False,
                "location_indexing": "章节或段落位置",
                "chunk_count": 1,
            },
            analysis_report_payload=build_fake_analysis_report(),
            voice_profile_payload=build_fake_voice_profile(),
        )
        await session.commit()

    create_profile_response = await initialized_client.post(
        "/api/v1/style-profiles",
        json={
            "job_id": job_id,
            "style_name": "王家卫风格（修订版）",
            "mount_project_id": project_id,
            "voice_profile_markdown": build_fake_voice_profile(),
        },
    )

    assert create_profile_response.status_code == 201
    profile = create_profile_response.json()
    assert profile["style_name"] == "王家卫风格（修订版）"
    assert profile["voice_profile_markdown"].startswith("# Voice Profile")
    assert profile["voice_profile_payload"]["common_expressions"]
    assert "style_summary_markdown" not in profile
    assert "prompt_pack_markdown" not in profile

    async with app_with_db.state.session_factory() as session:
        project = await session.scalar(select(Project).where(Project.id == project_id))
        assert project is not None
        assert project.style_profile_id == profile["id"]

    update_profile_response = await initialized_client.patch(
        f"/api/v1/style-profiles/{profile['id']}",
        json={
            "style_name": "王家卫风格（终版）",
            "voice_profile_markdown": build_fake_voice_profile().replace("短句推进", "更碎的短句推进"),
        },
    )
    assert update_profile_response.status_code == 200
    updated_profile = update_profile_response.json()
    assert "更碎的短句推进" in updated_profile["voice_profile_markdown"]


def test_build_style_profile_response_payload_only_depends_on_voice_profile_fields() -> None:
    profile = SimpleNamespace(
        id="profile-1",
        source_job_id="job-1",
        provider_id="provider-1",
        model_name="model-1",
        source_filename="sample.txt",
        style_name="冷白",
        analysis_report_payload=build_fake_analysis_report(),
        prompt_pack_payload=build_fake_voice_profile(),
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
    )

    payload = build_style_profile_response_payload(profile)
    assert payload["voice_profile_markdown"].startswith("# Voice Profile")
    assert payload["voice_profile_payload"].common_expressions
