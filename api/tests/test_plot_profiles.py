from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select

from app.api.assemblers import build_plot_profile_response_payload
from app.db.models import Project
from app.services.plot_analysis_jobs import PlotAnalysisJobService


def build_fake_plot_report() -> str:
    return "# 执行摘要\n这本书靠高压绑定、反截胡与关系失衡推进。\n"


def build_fake_plot_writing_guide() -> str:
    return (
        "# Plot Writing Guide\n"
        "## Core Plot Formula\n- 用压力迫使主角行动。\n\n"
        "## Chapter Progression Loop\n- 目标 -> 阻碍 -> 行动 -> 小兑现 -> 新压力。\n\n"
        "## Scene Construction Rules\n- 每个场景必须改变局面。\n\n"
        "## Setup and Payoff Rules\n- 伏笔必须参与行动兑现。\n\n"
        "## Payoff and Tension Rhythm\n- 半兑现后追加更大压力。\n\n"
        "## Side Plot Usage\n- 支线必须回流主线。\n\n"
        "## Hook Recipes\n- 胜利后揭示代价。\n\n"
        "## Anti-Drift Rules\n- 不要复述样本剧情。\n"
    )


@pytest.mark.asyncio
async def test_create_and_update_plot_profile_from_succeeded_job_and_mount_project(
    initialized_client: AsyncClient,
    app_with_db: FastAPI,
    initialized_provider: dict[str, object],
) -> None:
    provider_id = str(initialized_provider["id"])

    project_response = await initialized_client.post(
        "/api/v1/projects",
        json={
            "name": "情节挂载项目",
            "description": "用于验证情节档案挂载",
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
        "/api/v1/plot-analysis-jobs",
        data={"plot_name": "宗门夺位", "provider_id": provider_id},
        files={"file": ("sample.txt", "第一章 风雪夜归人".encode("utf-8"), "text/plain")},
    )
    job_id = create_job_response.json()["id"]

    async with app_with_db.state.session_factory() as session:
        await PlotAnalysisJobService().mark_job_succeeded(
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
            analysis_report_payload=build_fake_plot_report(),
            story_engine_payload=build_fake_plot_writing_guide(),
            plot_skeleton_payload="# 全书骨架\n启动期\n",
        )
        await session.commit()

    create_profile_response = await initialized_client.post(
        "/api/v1/plot-profiles",
        json={
            "job_id": job_id,
            "plot_name": "宗门夺位（修订版）",
            "mount_project_id": project_id,
            "story_engine_markdown": build_fake_plot_writing_guide(),
            "plot_skeleton_markdown": "# 全书骨架\n启动期\n",
        },
    )

    assert create_profile_response.status_code == 201
    profile = create_profile_response.json()
    assert profile["story_engine_markdown"].startswith("# Plot Writing Guide")
    assert profile["story_engine_payload"]["core_plot_formula"]
    assert "suggested_overlays" not in profile
    assert "plot_summary_markdown" not in profile
    assert "prompt_pack_markdown" not in profile

    async with app_with_db.state.session_factory() as session:
        project = await session.scalar(select(Project).where(Project.id == project_id))
        assert project is not None
        assert project.plot_profile_id == profile["id"]

    update_profile_response = await initialized_client.patch(
        f"/api/v1/plot-profiles/{profile['id']}",
        json={
            "plot_name": "宗门夺位（终版）",
            "story_engine_markdown": build_fake_plot_writing_guide().replace("迫使主角行动", "制造主动选择"),
        },
    )
    assert update_profile_response.status_code == 200
    updated_profile = update_profile_response.json()
    assert "制造主动选择" in " ".join(updated_profile["story_engine_payload"]["core_plot_formula"])


def test_build_plot_profile_response_payload_only_depends_on_story_engine_fields() -> None:
    profile = SimpleNamespace(
        id="profile-1",
        source_job_id="job-1",
        provider_id="provider-1",
        model_name="model-1",
        source_filename="sample.txt",
        plot_name="宗门夺位",
        analysis_report_payload=build_fake_plot_report(),
        story_engine_payload=build_fake_plot_writing_guide(),
        plot_skeleton_payload="# 全书骨架\n启动期\n",
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
    )

    payload = build_plot_profile_response_payload(profile)
    assert payload["story_engine_markdown"].startswith("# Plot Writing Guide")
    assert payload["story_engine_payload"].core_plot_formula
    assert "suggested_overlays" not in payload
