from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.services.style_analysis_jobs import StyleAnalysisJobService


def build_fake_analysis_report() -> dict:
    sections = []
    for section_no, title in [
        ("3.1", "口头禅与常用表达"),
        ("3.2", "固定句式与节奏偏好"),
        ("3.3", "词汇选择偏好"),
        ("3.4", "句子构造习惯"),
        ("3.5", "生活经历线索"),
        ("3.6", "行业／地域词汇"),
        ("3.7", "自然化缺陷"),
        ("3.8", "写作忌口与避讳"),
        ("3.9", "比喻口味与意象库"),
        ("3.10", "思维模式与表达逻辑"),
        ("3.11", "常见场景的说话方式"),
        ("3.12", "个人价值取向与反复母题"),
    ]:
        sections.append(
            {
                "section": section_no,
                "title": title,
                "overview": f"{title}的全局概览。",
                "findings": [
                    {
                        "label": f"{title}发现 1",
                        "summary": f"{title}的关键结论。",
                        "frequency": "高频",
                        "confidence": "high",
                        "is_weak_judgment": False,
                        "evidence": [
                            {"excerpt": "雨下得很慢。", "location": "段落 1"},
                        ],
                    }
                ],
            }
        )
    return {
        "executive_summary": {
            "summary": "整体文风缓慢、潮湿、情绪延迟。",
            "representative_evidence": [
                {"excerpt": "雨下得很慢。", "location": "段落 1"},
                {"excerpt": "时间也很慢。", "location": "段落 1"},
            ],
        },
        "basic_assessment": {
            "text_type": "章节正文",
            "multi_speaker": False,
            "batch_mode": False,
            "location_indexing": "章节或段落位置",
            "noise_handling": "未发现显著噪声。",
        },
        "sections": sections,
        "appendix": "当前样本较短，附录省略详细索引。",
    }


def build_fake_style_summary(style_name: str) -> dict:
    return {
        "style_name": style_name,
        "style_positioning": "迟滞、潮湿、回望感强。",
        "core_features": ["缓慢节奏", "潮湿意象", "回忆感"],
        "lexical_preferences": ["雨", "时间", "房间"],
        "rhythm_profile": ["舒缓句式", "停顿明显"],
        "punctuation_profile": ["句号偏多", "转折停顿多"],
        "imagery_and_themes": ["霓虹", "潮湿", "室内空气"],
        "scene_strategies": [
            {"scene": "dialogue", "instruction": "对白短促，保留言外之意。"},
            {"scene": "environment", "instruction": "环境描写带潮湿和霓虹感。"},
        ],
        "avoid_or_rare": ["避免直白喊口号。"],
        "generation_notes": ["优先维持缓慢、回望的叙述速度。"],
    }


def build_fake_prompt_pack() -> dict:
    return {
        "system_prompt": "以迟滞、潮湿、回望感强的中文小说文风进行创作。",
        "scene_prompts": {
            "dialogue": "对白短促，带停顿和言外之意。",
            "action": "动作描写轻，重点放在情绪余波。",
            "environment": "环境描写突出潮湿、霓虹和室内空气感。",
        },
        "hard_constraints": ["避免口号式抒情。", "避免现代网络口吻。"],
        "style_controls": {
            "tone": "迟滞而克制",
            "rhythm": "舒缓推进",
            "evidence_anchor": "优先保留报告中的高置信特征",
        },
        "few_shot_slots": [
            {
                "label": "environment",
                "type": "environment",
                "text": "楼道里有一盏旧灯，亮了又暗。",
                "purpose": "建立潮湿室内氛围",
            },
            {
                "label": "dialogue",
                "type": "dialogue",
                "text": "她说再见的时候，像是在说别的事。",
                "purpose": "示范克制对白",
            },
        ],
    }


@pytest.mark.asyncio
async def test_create_and_update_style_profile_from_succeeded_job_and_mount_project(
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

    async def fake_classify_input(self, *, text: str) -> dict:
        assert "雨下得很慢" in text
        return {
            "text_type": "章节正文",
            "has_timestamps": False,
            "has_speaker_labels": False,
            "has_noise_markers": False,
            "uses_batch_processing": False,
            "location_indexing": "章节或段落位置",
            "noise_notes": "未发现显著噪声。",
        }

    async def fake_analyze_chunks(self, *, chunks: list[str], classification: dict) -> list[dict]:
        del classification
        assert len(chunks) == 1
        return [{"chunk_index": 0, "summary": "局部结果"}]

    async def fake_merge_chunk_analyses(self, *, chunk_analyses: list[dict], classification: dict) -> dict:
        del classification
        assert chunk_analyses[0]["chunk_index"] == 0
        return {"merged": True}

    async def fake_build_analysis_report(self, *, merged_analysis: dict, classification: dict) -> dict:
        del merged_analysis, classification
        return build_fake_analysis_report()

    async def fake_build_style_summary(self, *, report: dict) -> dict:
        del report
        return build_fake_style_summary("王家卫风格")

    async def fake_build_prompt_pack(self, *, report: dict, style_summary: dict) -> dict:
        del report
        assert style_summary["style_name"] == "王家卫风格"
        return build_fake_prompt_pack()

    monkeypatch.setattr(StyleAnalysisJobService, "_classify_input", fake_classify_input)
    monkeypatch.setattr(StyleAnalysisJobService, "_analyze_chunks", fake_analyze_chunks)
    monkeypatch.setattr(StyleAnalysisJobService, "_merge_chunk_analyses", fake_merge_chunk_analyses)
    monkeypatch.setattr(StyleAnalysisJobService, "_build_analysis_report", fake_build_analysis_report)
    monkeypatch.setattr(StyleAnalysisJobService, "_build_style_summary", fake_build_style_summary)
    monkeypatch.setattr(StyleAnalysisJobService, "_build_prompt_pack", fake_build_prompt_pack)

    processed = await StyleAnalysisJobService().process_next_pending(app_with_db.state.session_factory)
    assert processed is True

    create_profile_response = await initialized_client.post(
        "/api/v1/style-profiles",
        json={
            "job_id": job_id,
            "style_summary": {
                **build_fake_style_summary("王家卫风格（修订版）"),
                "style_name": "王家卫风格（修订版）",
            },
            "prompt_pack": {
                **build_fake_prompt_pack(),
                "system_prompt": "以迟滞、潮湿、都市孤独感为核心进行创作。",
            },
        },
    )

    assert create_profile_response.status_code == 201
    profile = create_profile_response.json()
    assert profile["style_name"] == "王家卫风格（修订版）"
    assert profile["source_job_id"] == job_id
    assert profile["provider_id"] == provider_id
    assert profile["source_filename"] == "sample.txt"
    assert profile["analysis_report"]["sections"][0]["section"] == "3.1"
    assert profile["style_summary"]["style_name"] == "王家卫风格（修订版）"
    assert profile["prompt_pack"]["system_prompt"].startswith("以迟滞")

    update_profile_response = await initialized_client.patch(
        f"/api/v1/style-profiles/{profile['id']}",
        json={
            "style_summary": {
                **profile["style_summary"],
                "generation_notes": ["突出潮湿感与延迟情绪。"],
            },
            "prompt_pack": {
                **profile["prompt_pack"],
                "hard_constraints": ["避免口号式抒情。"],
            },
        },
    )
    assert update_profile_response.status_code == 200
    updated_profile = update_profile_response.json()
    assert updated_profile["style_summary"]["generation_notes"] == ["突出潮湿感与延迟情绪。"]
    assert updated_profile["prompt_pack"]["hard_constraints"] == ["避免口号式抒情。"]

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
