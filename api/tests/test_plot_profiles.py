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


def build_fake_story_engine() -> str:
    return (
        "# Story Engine Profile\n"
        "## genre_mother\n- xianxia\n\n"
        "## drive_axes\n- 升级\n- 掠夺\n\n"
        "## payoff_objects\n- 力量\n- 资源\n\n"
        "## pressure_formulas\n- 宗门压制 -> 反制夺位\n\n"
        "## relation_roles\n- 奖励源\n- 压迫源\n\n"
        "## scene_verbs\n- 入局\n- 压制\n- 收割\n\n"
        "## hook_recipes\n- 半兑现后立刻追加新压力\n\n"
        "## anti_drift_guardrails\n- 不要退化成纯气氛描写\n\n"
        "## suggested_overlays\n- harem_collect\n"
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
            story_engine_payload=build_fake_story_engine(),
            plot_skeleton_payload="# 全书骨架\n启动期\n",
        )
        await session.commit()

    create_profile_response = await initialized_client.post(
        "/api/v1/plot-profiles",
        json={
            "job_id": job_id,
            "plot_name": "宗门夺位（修订版）",
            "mount_project_id": project_id,
            "story_engine_markdown": build_fake_story_engine(),
            "plot_skeleton_markdown": "# 全书骨架\n启动期\n",
        },
    )

    assert create_profile_response.status_code == 201
    profile = create_profile_response.json()
    assert profile["story_engine_markdown"].startswith("# Story Engine Profile")
    assert profile["story_engine_payload"]["genre_mother"] == "xianxia"
    assert profile["suggested_overlays"] == ["harem_collect"]
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
            "story_engine_markdown": build_fake_story_engine().replace("xianxia", "urban"),
        },
    )
    assert update_profile_response.status_code == 200
    updated_profile = update_profile_response.json()
    assert updated_profile["story_engine_payload"]["genre_mother"] == "urban"


def test_build_plot_profile_response_payload_only_depends_on_story_engine_fields() -> None:
    profile = SimpleNamespace(
        id="profile-1",
        source_job_id="job-1",
        provider_id="provider-1",
        model_name="model-1",
        source_filename="sample.txt",
        plot_name="宗门夺位",
        analysis_report_payload=build_fake_plot_report(),
        prompt_pack_payload=build_fake_story_engine(),
        plot_skeleton_payload="# 全书骨架\n启动期\n",
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
    )

    payload = build_plot_profile_response_payload(profile)
    assert payload["story_engine_markdown"].startswith("# Story Engine Profile")
    assert payload["story_engine_payload"].genre_mother == "xianxia"
    assert payload["suggested_overlays"] == ["harem_collect"]
