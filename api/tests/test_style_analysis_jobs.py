from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy import select

from app.db.models import StyleAnalysisJob
from app.schemas.style_analysis_jobs import (
    AnalysisMeta,
    AnalysisReport,
    PromptPack,
    StyleAnalysisJobResponse,
    StyleSummary,
)
from app.services.style_analysis_jobs import StyleAnalysisJobService, build_job_result_bundle
from app.services.style_analysis_worker import StyleAnalysisWorkerService
from app.services.style_analysis_pipeline import StyleAnalysisPipelineResult


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
                            {"excerpt": "夜色很冷。", "location": "段落 1"},
                        ],
                    }
                ],
            }
        )
    return {
        "executive_summary": {
            "summary": "整体文风冷峻、短句密集、留白明显。",
            "representative_evidence": [
                {"excerpt": "夜色很冷。", "location": "段落 1"},
                {"excerpt": "他忽然笑了。", "location": "段落 2"},
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
        "style_positioning": "冷峻、克制、短句驱动。",
        "core_features": ["短句推进", "留白明显", "冷感意象密集"],
        "lexical_preferences": ["冷", "笑", "忽然"],
        "rhythm_profile": ["短句为主", "停顿明显"],
        "punctuation_profile": ["句号收束多", "省略号稀少"],
        "imagery_and_themes": ["夜色", "孤独", "试探"],
        "scene_strategies": [
            {"scene": "dialogue", "instruction": "对白尽量短，带试探与克制。"},
            {"scene": "action", "instruction": "动作描写利落，不铺陈多余细节。"},
        ],
        "avoid_or_rare": ["避免长篇抒情和华丽排比。"],
        "generation_notes": ["优先保留冷感词和短句节奏。"],
    }


def build_fake_prompt_pack() -> dict:
    return {
        "system_prompt": "以冷峻、克制、留白明显的中文小说文风进行创作。",
        "scene_prompts": {
            "dialogue": "对白短促，保留言外之意。",
            "action": "动作描写要干净利落。",
            "environment": "环境描写服务情绪，不堆砌形容词。",
        },
        "hard_constraints": ["避免现代网络口吻。", "避免抒情堆砌。"],
        "style_controls": {
            "tone": "冷峻克制",
            "rhythm": "短句驱动",
            "evidence_anchor": "优先使用报告中的高置信特征",
        },
        "few_shot_slots": [
            {
                "label": "environment",
                "type": "environment",
                "text": "夜色像一把薄刀，贴着窗纸划过去。",
                "purpose": "建立冷感氛围",
            },
            {
                "label": "dialogue",
                "type": "dialogue",
                "text": "他笑了笑，说这不算什么。",
                "purpose": "示范节制对白",
            },
        ],
    }


def build_style_analysis_job_response_payload() -> dict:
    now = datetime.now(UTC)
    return {
        "id": "job-1",
        "style_name": "测试风格",
        "provider_id": "provider-1",
        "model_name": "gpt-4.1-mini",
        "status": "running",
        "stage": "preparing_input",
        "error_message": None,
        "started_at": now,
        "completed_at": None,
        "created_at": now,
        "updated_at": now,
        "provider": {
            "id": "provider-1",
            "label": "Primary Gateway",
            "base_url": "https://api.openai.com/v1",
            "default_model": "gpt-4.1-mini",
            "is_enabled": True,
        },
        "sample_file": {
            "id": "sample-1",
            "original_filename": "sample.txt",
            "content_type": "text/plain",
            "byte_size": 12,
            "character_count": 4,
            "checksum_sha256": "abc123",
            "created_at": now,
            "updated_at": now,
        },
        "style_profile_id": None,
        "analysis_meta": None,
        "analysis_report": None,
        "style_summary": None,
        "prompt_pack": None,
    }


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
    assert "analysis_meta" not in created
    assert "analysis_report" not in created
    assert "style_summary" not in created
    assert "prompt_pack" not in created
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
async def test_process_next_pending_job_generates_analysis_bundle_and_updates_job_detail(
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

    async def fake_build_pipeline(
        self,
        *,
        provider,
        model_name: str,
        style_name: str,
        source_filename: str,
        stage_callback,
    ):
        del provider, stage_callback
        assert model_name
        assert style_name == "古龙风格实验"
        assert source_filename == "sample.txt"

        class FakePipeline:
            async def run(
                self,
                *,
                thread_id: str,
                chunks: list[str],
                classification: dict,
                max_concurrency: int,
            ) -> StyleAnalysisPipelineResult:
                assert thread_id == job_id
                assert len(chunks) == 1
                assert classification["text_type"] == "章节正文"
                assert max_concurrency == 5
                report = build_fake_analysis_report()
                return StyleAnalysisPipelineResult(
                    analysis_meta=AnalysisMeta(
                        source_filename="sample.txt",
                        model_name=model_name,
                        text_type="章节正文",
                        has_timestamps=False,
                        has_speaker_labels=False,
                        has_noise_markers=False,
                        uses_batch_processing=False,
                        location_indexing="章节或段落位置",
                        chunk_count=1,
                    ),
                    analysis_report=AnalysisReport.model_validate(report),
                    style_summary=StyleSummary.model_validate(
                        build_fake_style_summary("古龙风格实验")
                    ),
                    prompt_pack=PromptPack.model_validate(build_fake_prompt_pack()),
                )

        return FakePipeline()

    monkeypatch.setattr(StyleAnalysisWorkerService, "_build_pipeline", fake_build_pipeline)

    processed = await StyleAnalysisWorkerService().process_next_pending(app_with_db.state.session_factory)
    assert processed is True

    detail_response = await initialized_client.get(f"/api/v1/style-analysis-jobs/{job_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["status"] == "succeeded"
    assert detail["stage"] is None
    assert detail["error_message"] is None
    assert detail["sample_file"]["character_count"] == len("夜色很冷。\n\n他忽然笑了。")

    meta_response = await initialized_client.get(
        f"/api/v1/style-analysis-jobs/{job_id}/analysis-meta"
    )
    assert meta_response.status_code == 200
    assert meta_response.json()["text_type"] == "章节正文"
    assert meta_response.json()["uses_batch_processing"] is False

    report_response = await initialized_client.get(
        f"/api/v1/style-analysis-jobs/{job_id}/analysis-report"
    )
    assert report_response.status_code == 200
    assert len(report_response.json()["sections"]) == 12
    assert report_response.json()["sections"][0]["section"] == "3.1"

    summary_response = await initialized_client.get(
        f"/api/v1/style-analysis-jobs/{job_id}/style-summary"
    )
    assert summary_response.status_code == 200
    assert summary_response.json()["style_name"] == "古龙风格实验"

    prompt_pack_response = await initialized_client.get(
        f"/api/v1/style-analysis-jobs/{job_id}/prompt-pack"
    )
    assert prompt_pack_response.status_code == 200
    assert prompt_pack_response.json()["system_prompt"].startswith("以冷峻")


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

    import app.services.style_analysis_worker as style_analysis_worker_module

    def fake_read_chunks_and_classification(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("输入判定失败")

    monkeypatch.setattr(
        style_analysis_worker_module,
        "read_chunks_and_classification",
        fake_read_chunks_and_classification,
    )

    processed = await StyleAnalysisWorkerService().process_next_pending(app_with_db.state.session_factory)
    assert processed is True

    detail_response = await initialized_client.get(f"/api/v1/style-analysis-jobs/{job_id}")
    detail = detail_response.json()
    assert detail["status"] == "failed"
    assert detail["error_message"] == "输入判定失败"


@pytest.mark.asyncio
async def test_claim_next_pending_job_claims_once_and_records_lease(
    initialized_client: AsyncClient,
    app_with_db: FastAPI,
) -> None:
    provider_id = (await initialized_client.get("/api/v1/provider-configs")).json()[0]["id"]
    create_response = await initialized_client.post(
        "/api/v1/style-analysis-jobs",
        data={"style_name": "并发任务", "provider_id": provider_id},
        files={"file": ("sample.txt", "山风很急。".encode("utf-8"), "text/plain")},
    )
    job_id = create_response.json()["id"]
    service = StyleAnalysisWorkerService()

    first_claim = await service._claim_next_pending_job(
        app_with_db.state.session_factory,
        worker_id="worker-a",
    )
    second_claim = await service._claim_next_pending_job(
        app_with_db.state.session_factory,
        worker_id="worker-b",
    )

    assert first_claim == job_id
    assert second_claim is None
    async with app_with_db.state.session_factory() as session:
        job = await session.scalar(select(StyleAnalysisJob).where(StyleAnalysisJob.id == job_id))
        assert job is not None
        assert job.status == "running"
        assert job.stage == "preparing_input"
        assert job.locked_by == "worker-a"
        assert job.locked_at is not None
        assert job.last_heartbeat_at is not None
        assert job.attempt_count == 1


@pytest.mark.asyncio
async def test_app_startup_releases_stale_running_jobs_for_resume(
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
        job.stage = "analyzing_chunks"
        job.started_at = datetime.now(UTC) - timedelta(minutes=10)
        job.locked_by = "dead-worker"
        job.locked_at = datetime.now(UTC) - timedelta(minutes=10)
        job.last_heartbeat_at = datetime.now(UTC) - timedelta(minutes=10)
        job.attempt_count = 1
        await session.commit()

    async with LifespanManager(app_with_db):
        pass

    detail_response = await initialized_client.get(f"/api/v1/style-analysis-jobs/{job_id}")
    detail = detail_response.json()
    assert detail["status"] == "pending"
    assert detail["stage"] is None
    assert detail["error_message"] is None
    async with app_with_db.state.session_factory() as session:
        job = await session.scalar(select(StyleAnalysisJob).where(StyleAnalysisJob.id == job_id))
        assert job is not None
        assert job.locked_by is None
        assert job.locked_at is None
        assert job.last_heartbeat_at is None
        assert job.attempt_count == 1


def test_build_job_result_bundle_does_not_fallback_to_legacy_draft_payload() -> None:
    job = SimpleNamespace(
        analysis_meta_payload=None,
        analysis_report_payload=None,
        style_summary_payload=None,
        prompt_pack_payload=None,
        draft_payload={
            "analysis_summary": "旧版摘要",
            "global_system_prompt": "旧版系统提示词",
            "dimensions": {"core_features": ["旧版"]},
            "scene_prompts": {"dialogue": "旧版对白"},
            "few_shot_examples": [{"text": "旧版示例"}],
        },
        style_name="旧版风格",
        sample_file=SimpleNamespace(original_filename="legacy.txt"),
        model_name="legacy-model",
    )
    analysis_meta, analysis_report, style_summary, prompt_pack = build_job_result_bundle(job)
    assert analysis_meta is None
    assert analysis_report is None
    assert style_summary is None
    assert prompt_pack is None


def test_style_analysis_job_response_accepts_allowed_status_and_stage() -> None:
    payload = build_style_analysis_job_response_payload()
    response = StyleAnalysisJobResponse.model_validate(payload)
    assert response.status == "running"
    assert response.stage == "preparing_input"


def test_style_analysis_job_response_rejects_unknown_status() -> None:
    payload = build_style_analysis_job_response_payload()
    payload["status"] = "done"
    with pytest.raises(ValidationError):
        StyleAnalysisJobResponse.model_validate(payload)


def test_style_analysis_job_response_rejects_legacy_stage() -> None:
    payload = build_style_analysis_job_response_payload()
    payload["stage"] = "classifying_input"
    with pytest.raises(ValidationError):
        StyleAnalysisJobResponse.model_validate(payload)
