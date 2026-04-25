from __future__ import annotations

from fastapi import FastAPI
from httpx import AsyncClient

import pytest

from app.services.style_analysis_jobs import StyleAnalysisJobService


def build_fake_analysis_report() -> str:
    return "# 执行摘要\n整体文风冷峻、短句密集、留白明显。\n"


def build_fake_voice_profile() -> str:
    return (
        "# Voice Profile\n"
        "## sentence_rhythm\n- 短句推进\n\n"
        "## narrative_distance\n- 贴近主角\n\n"
        "## detail_anchors\n- 呼吸\n- 视线\n\n"
        "## dialogue_aggression\n- 试探与抢拍\n\n"
        "## irregularity_budget\n- 轻微断裂\n\n"
        "## anti_ai_guardrails\n- 禁止解释腔\n"
    )


@pytest.mark.asyncio
async def test_create_style_analysis_job_persists_txt_and_exposes_list_item_only(
    initialized_client: AsyncClient,
    initialized_provider: dict[str, object],
) -> None:
    provider_id = str(initialized_provider["id"])

    create_response = await initialized_client.post(
        "/api/v1/style-analysis-jobs",
        data={
            "style_name": "金庸武侠风",
            "provider_id": provider_id,
            "model": str(initialized_provider["default_model"]),
        },
        files={"file": ("sample.txt", "第一章 风雪夜归人\n\n郭靖抬头望去。".encode("utf-8"), "text/plain")},
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["style_name"] == "金庸武侠风"
    assert created["status"] == "pending"
    assert "voice_profile_markdown" not in created
    assert "voice_profile_payload" not in created


@pytest.mark.asyncio
async def test_style_analysis_job_detail_returns_voice_profile_fields(
    initialized_client: AsyncClient,
    initialized_provider: dict[str, object],
    app_with_db: FastAPI,
) -> None:
    provider_id = str(initialized_provider["id"])
    create_response = await initialized_client.post(
        "/api/v1/style-analysis-jobs",
        data={
            "style_name": "古龙风格实验",
            "provider_id": provider_id,
        },
        files={"file": ("sample.txt", "第一章 风雪夜归人".encode("utf-8"), "text/plain")},
    )
    job_id = create_response.json()["id"]

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

    detail_response = await initialized_client.get(f"/api/v1/style-analysis-jobs/{job_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["analysis_report_markdown"].startswith("# 执行摘要")
    assert detail["voice_profile_markdown"].startswith("# Voice Profile")
    assert detail["voice_profile_payload"]["sentence_rhythm"]
    assert "style_summary_markdown" not in detail
    assert "prompt_pack_markdown" not in detail

    voice_profile_response = await initialized_client.get(
        f"/api/v1/style-analysis-jobs/{job_id}/voice-profile"
    )
    assert voice_profile_response.status_code == 200
    assert voice_profile_response.json().startswith("# Voice Profile")
