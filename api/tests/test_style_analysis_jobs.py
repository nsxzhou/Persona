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
    assert detail["voice_profile_payload"]["common_expressions"]
    assert "style_summary_markdown" not in detail
    assert "prompt_pack_markdown" not in detail

    voice_profile_response = await initialized_client.get(
        f"/api/v1/style-analysis-jobs/{job_id}/voice-profile"
    )
    assert voice_profile_response.status_code == 200
    assert voice_profile_response.json().startswith("# Voice Profile")
