from __future__ import annotations

from fastapi import FastAPI
from httpx import AsyncClient

import pytest

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
async def test_plot_analysis_job_detail_returns_story_engine_fields(
    initialized_client: AsyncClient,
    initialized_provider: dict[str, object],
    app_with_db: FastAPI,
) -> None:
    provider_id = str(initialized_provider["id"])
    create_response = await initialized_client.post(
        "/api/v1/plot-analysis-jobs",
        data={"plot_name": "宗门夺位", "provider_id": provider_id},
        files={"file": ("sample.txt", "第一章 风雪夜归人".encode("utf-8"), "text/plain")},
    )
    job_id = create_response.json()["id"]

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

    detail_response = await initialized_client.get(f"/api/v1/plot-analysis-jobs/{job_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["analysis_report_markdown"].startswith("# 执行摘要")
    assert detail["story_engine_markdown"].startswith("# Story Engine Profile")
    assert detail["story_engine_payload"]["genre_mother"] == "xianxia"
    assert detail["suggested_overlays"] == ["harem_collect"]
    assert "plot_summary_markdown" not in detail
    assert "prompt_pack_markdown" not in detail

    story_engine_response = await initialized_client.get(
        f"/api/v1/plot-analysis-jobs/{job_id}/story-engine"
    )
    assert story_engine_response.status_code == 200
    assert story_engine_response.json().startswith("# Story Engine Profile")
