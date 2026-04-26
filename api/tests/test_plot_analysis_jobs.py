from __future__ import annotations

from fastapi import FastAPI
from httpx import AsyncClient

import pytest

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
            story_engine_payload=build_fake_plot_writing_guide(),
            plot_skeleton_payload="# 全书骨架\n启动期\n",
        )
        await session.commit()

    detail_response = await initialized_client.get(f"/api/v1/plot-analysis-jobs/{job_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["analysis_report_markdown"].startswith("# 执行摘要")
    assert detail["story_engine_markdown"].startswith("# Plot Writing Guide")
    assert detail["story_engine_payload"]["core_plot_formula"]
    assert "suggested_overlays" not in detail
    assert "plot_summary_markdown" not in detail
    assert "prompt_pack_markdown" not in detail

    story_engine_response = await initialized_client.get(
        f"/api/v1/plot-analysis-jobs/{job_id}/story-engine"
    )
    assert story_engine_response.status_code == 200
    assert story_engine_response.json().startswith("# Plot Writing Guide")
