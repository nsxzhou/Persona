from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy import inspect as sa_inspect, select

from app.core.config import get_settings
from app.db.models import StyleAnalysisJob, StyleProfile
from app.db.repositories.style_analysis_jobs import StyleAnalysisJobRepository
from app.main import create_app
from app.schemas.style_analysis_jobs import (
    AnalysisMeta,
    AnalysisReport,
    PromptPack,
    StyleAnalysisJobResponse,
    StyleSummary,
)
from app.services.style_analysis_jobs import StyleAnalysisJobService, build_job_result_bundle
from app.services.style_analysis_worker import (
    StyleAnalysisRunContext,
    StyleAnalysisWorkerService,
)
from app.services.style_analysis_pipeline import StyleAnalysisPipeline, StyleAnalysisPipelineResult
from app.services.style_analysis_storage import StyleAnalysisStorageService


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
async def test_get_detail_or_404_fetches_job_once_when_payload_is_present() -> None:
    analysis_meta = AnalysisMeta(
        source_filename="sample.txt",
        model_name="gpt-4.1-mini",
        text_type="章节正文",
        has_timestamps=False,
        has_speaker_labels=False,
        has_noise_markers=False,
        uses_batch_processing=False,
        location_indexing="章节或段落位置",
        chunk_count=1,
    ).model_dump(mode="json")

    job = SimpleNamespace(
        id="job-1",
        style_name="测试风格",
        provider_id="provider-1",
        model_name="gpt-4.1-mini",
        status="succeeded",
        stage=None,
        error_message=None,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        provider=SimpleNamespace(
            id="provider-1",
            label="Primary Gateway",
            base_url="https://api.openai.com/v1",
            default_model="gpt-4.1-mini",
            is_enabled=True,
        ),
        sample_file=SimpleNamespace(
            id="sample-1",
            original_filename="sample.txt",
            content_type="text/plain",
            byte_size=12,
            character_count=12,
            checksum_sha256="abc123",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ),
        style_profile=None,
        style_profile_id=None,
        analysis_meta_payload=analysis_meta,
        analysis_report_payload=build_fake_analysis_report(),
        style_summary_payload=build_fake_style_summary("测试风格"),
        prompt_pack_payload=build_fake_prompt_pack(),
    )

    class RepositoryStub:
        def __init__(self) -> None:
            self.calls: list[tuple[bool, bool]] = []

        async def get_by_id(
            self,
            session,
            job_id: str,
            *,
            include_payloads: bool = True,
            include_style_profile_payloads: bool = True,
        ):
            del session
            assert job_id == "job-1"
            self.calls.append((include_payloads, include_style_profile_payloads))
            return job

    repository = RepositoryStub()
    service = StyleAnalysisJobService(repository=repository)  # type: ignore[arg-type]

    response = await service.get_detail_or_404(session=SimpleNamespace(), job_id="job-1")

    assert response.id == "job-1"
    assert len(repository.calls) == 1


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
                job_id: str,
                chunk_count: int,
                classification: dict,
                max_concurrency: int,
            ) -> StyleAnalysisPipelineResult:
                assert job_id == create_response.json()["id"]
                assert chunk_count == 1
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
    assert detail["analysis_meta"]["text_type"] == "章节正文"
    assert detail["analysis_report"]["sections"][0]["section"] == "3.1"
    assert detail["style_summary"]["style_name"] == "古龙风格实验"
    assert detail["prompt_pack"]["system_prompt"].startswith("以冷峻")
    assert detail["style_profile"] is None

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
    artifact_dir = Path(get_settings().storage_dir) / "style-analysis-artifacts" / job_id
    assert artifact_dir.exists() is False


@pytest.mark.asyncio
async def test_process_next_pending_job_records_retryable_failure_message(
    initialized_client: AsyncClient,
    app_with_db: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
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

    with caplog.at_level("ERROR", logger="app.services.style_analysis_worker"):
        processed = await StyleAnalysisWorkerService().process_next_pending(
            app_with_db.state.session_factory
        )
    assert processed is True

    detail_response = await initialized_client.get(f"/api/v1/style-analysis-jobs/{job_id}")
    detail = detail_response.json()
    assert detail["status"] == "pending"
    assert detail["error_message"] == "分析任务失败，请稍后重试。"
    assert "输入判定失败" in caplog.text
    assert any(getattr(record, "job_id", None) == job_id for record in caplog.records)


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
async def test_claim_pending_job_uses_single_atomic_update_statement() -> None:
    repository = StyleAnalysisJobRepository()

    class FakeResult:
        def __init__(self, claimed_id: str | None) -> None:
            self.claimed_id = claimed_id

        def scalar_one_or_none(self) -> str | None:
            return self.claimed_id

    class FakeSession:
        def __init__(self) -> None:
            self.execute_calls = 0

        async def scalar(self, stmt):
            del stmt
            raise AssertionError("claim_pending_job should not pre-select candidate id")

        async def execute(self, stmt):
            del stmt
            self.execute_calls += 1
            return FakeResult("job-1")

    fake_session = FakeSession()
    claimed_id = await repository.claim_pending_job(
        fake_session,  # type: ignore[arg-type]
        worker_id="worker-a",
        max_attempts=3,
        preparing_stage="preparing_input",
        running_status="running",
        pending_status="pending",
        now=datetime.now(UTC),
    )

    assert claimed_id == "job-1"
    assert fake_session.execute_calls == 1


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


@pytest.mark.asyncio
async def test_job_list_loads_style_profile_id_without_profile_payloads(
    initialized_client: AsyncClient,
    app_with_db: FastAPI,
) -> None:
    provider_id = (await initialized_client.get("/api/v1/provider-configs")).json()[0]["id"]
    create_response = await initialized_client.post(
        "/api/v1/style-analysis-jobs",
        data={"style_name": "列表载荷任务", "provider_id": provider_id},
        files={"file": ("sample.txt", "第一段。".encode("utf-8"), "text/plain")},
    )
    job_id = create_response.json()["id"]
    report = build_fake_analysis_report()
    summary = build_fake_style_summary("列表载荷任务")
    prompt_pack = build_fake_prompt_pack()

    async with app_with_db.state.session_factory() as session:
        job = await StyleAnalysisJobService().get_or_404(session, job_id)
        job.status = "succeeded"
        job.analysis_meta_payload = AnalysisMeta(
            source_filename="sample.txt",
            model_name=job.model_name,
            text_type="章节正文",
            has_timestamps=False,
            has_speaker_labels=False,
            has_noise_markers=False,
            uses_batch_processing=False,
            location_indexing="章节或段落位置",
            chunk_count=1,
        ).model_dump(mode="json")
        job.analysis_report_payload = report
        job.style_summary_payload = summary
        job.prompt_pack_payload = prompt_pack
        profile = StyleProfile(
            user_id=job.user_id,
            source_job_id=job.id,
            provider_id=provider_id,
            model_name=job.model_name,
            source_filename=job.sample_file.original_filename,
            style_name="列表载荷任务",
            analysis_report_payload=report,
            style_summary_payload=summary,
            prompt_pack_payload=prompt_pack,
        )
        session.add(profile)
        await session.commit()
        profile_id = profile.id

    async with app_with_db.state.session_factory() as session:
        jobs = await StyleAnalysisJobRepository().list(
            session,
            offset=0,
            limit=10,
            include_payloads=False,
        )
        assert len(jobs) == 1
        listed_job = jobs[0]
        assert listed_job.style_profile_id == profile_id
        assert listed_job.style_profile is not None
        unloaded = sa_inspect(listed_job.style_profile).unloaded
        assert "analysis_report_payload" in unloaded
        assert "style_summary_payload" in unloaded
        assert "prompt_pack_payload" in unloaded


@pytest.mark.asyncio
async def test_delete_style_analysis_job_removes_storage_and_unblocks_provider_delete(
    initialized_client: AsyncClient,
) -> None:
    provider_id = (await initialized_client.get("/api/v1/provider-configs")).json()[0]["id"]
    create_response = await initialized_client.post(
        "/api/v1/style-analysis-jobs",
        data={"style_name": "删除任务", "provider_id": provider_id},
        files={"file": ("sample.txt", "第一段。".encode("utf-8"), "text/plain")},
    )
    assert create_response.status_code == 201
    job = create_response.json()
    sample_file_id = job["sample_file"]["id"]

    sample_file_path = Path(get_settings().storage_dir) / "style-samples" / f"{sample_file_id}.txt"
    artifact_dir = Path(get_settings().storage_dir) / "style-analysis-artifacts" / job["id"]
    storage_service = StyleAnalysisStorageService()
    await storage_service.write_chunk_artifact(job["id"], 0, "中间产物")

    assert sample_file_path.exists() is True
    assert artifact_dir.exists() is True

    delete_job_response = await initialized_client.delete(f"/api/v1/style-analysis-jobs/{job['id']}")
    assert delete_job_response.status_code == 204
    assert sample_file_path.exists() is False
    assert artifact_dir.exists() is False

    delete_provider_response = await initialized_client.delete(f"/api/v1/provider-configs/{provider_id}")
    assert delete_provider_response.status_code == 204


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


@pytest.mark.asyncio
async def test_process_next_pending_job_cleans_chunk_artifacts_after_pipeline_failure(
    initialized_client: AsyncClient,
    app_with_db: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STYLE_ANALYSIS_MAX_ATTEMPTS", "1")
    get_settings.cache_clear()
    provider_id = (await initialized_client.get("/api/v1/provider-configs")).json()[0]["id"]
    create_response = await initialized_client.post(
        "/api/v1/style-analysis-jobs",
        data={"style_name": "失败清理任务", "provider_id": provider_id},
        files={"file": ("sample.txt", "第一段。\n\n第二段。".encode("utf-8"), "text/plain")},
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
        del provider, model_name, style_name, source_filename, stage_callback

        class FakePipeline:
            async def run(
                self,
                *,
                job_id: str,
                chunk_count: int,
                classification: dict,
                max_concurrency: int,
            ) -> StyleAnalysisPipelineResult:
                del chunk_count, classification, max_concurrency
                assert job_id
                raise RuntimeError("报告生成失败")

        return FakePipeline()

    monkeypatch.setattr(StyleAnalysisWorkerService, "_build_pipeline", fake_build_pipeline)

    processed = await StyleAnalysisWorkerService().process_next_pending(app_with_db.state.session_factory)
    assert processed is True

    detail_response = await initialized_client.get(f"/api/v1/style-analysis-jobs/{job_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["status"] == "failed"
    assert detail["error_message"] == "分析任务失败，请稍后重试。"
    artifact_dir = Path(get_settings().storage_dir) / "style-analysis-artifacts" / job_id
    assert artifact_dir.exists() is False
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_process_next_pending_job_resumes_retryable_checkpoint_without_reanalyzing_chunks(
    initialized_client: AsyncClient,
    app_with_db: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from langgraph.checkpoint.memory import InMemorySaver

    provider_id = (await initialized_client.get("/api/v1/provider-configs")).json()[0]["id"]
    create_response = await initialized_client.post(
        "/api/v1/style-analysis-jobs",
        data={"style_name": "可续跑任务", "provider_id": provider_id},
        files={"file": ("sample.txt", "第一段。\n\n第二段。\n\n第三段。".encode("utf-8"), "text/plain")},
    )
    job_id = create_response.json()["id"]

    class FakeStructuredLLMClient:
        def __init__(self) -> None:
            self.chunk_calls = 0
            self.report_calls = 0

        def build_model(self, *, provider, model_name: str):
            return SimpleNamespace(provider=provider, model_name=model_name)

        async def ainvoke_structured(self, *, model, schema, prompt: str):
            del model
            if schema is AnalysisReport:
                self.report_calls += 1
                if self.report_calls == 1:
                    raise RuntimeError("report transient failure")
                return AnalysisReport.model_validate(build_fake_analysis_report())
            if schema is StyleSummary:
                return StyleSummary.model_validate(build_fake_style_summary("可续跑任务"))
            if schema is PromptPack:
                return PromptPack.model_validate(build_fake_prompt_pack())
            if schema.__name__ == "MergedAnalysis":
                return schema.model_validate(
                    {"classification": {"text_type": "章节正文"}, "sections": build_fake_analysis_report()["sections"]}
                )
            if schema.__name__ == "ChunkAnalysis":
                self.chunk_calls += 1
                chunk_index = self.chunk_calls - 1
                return schema.model_validate(
                    {
                        "chunk_index": chunk_index,
                            "chunk_count": 1,
                            "sections": build_fake_analysis_report()["sections"],
                        }
                    )
            raise AssertionError(f"unexpected schema: {schema}")

    client = FakeStructuredLLMClient()
    checkpointer = InMemorySaver()

    async def fake_build_pipeline(
        self,
        *,
        provider,
        model_name: str,
        style_name: str,
        source_filename: str,
        stage_callback,
    ):
        return StyleAnalysisPipeline(
            provider=provider,
            model_name=model_name,
            style_name=style_name,
            source_filename=source_filename,
            llm_client=client,
            checkpointer=checkpointer,
            stage_callback=stage_callback,
        )

    monkeypatch.setattr(StyleAnalysisWorkerService, "_build_pipeline", fake_build_pipeline)

    service = StyleAnalysisWorkerService()
    processed = await service.process_next_pending(app_with_db.state.session_factory)
    assert processed is True

    detail_response = await initialized_client.get(f"/api/v1/style-analysis-jobs/{job_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["status"] == "pending"
    assert detail["error_message"] == "分析任务失败，请稍后重试。"
    artifact_dir = Path(get_settings().storage_dir) / "style-analysis-artifacts" / job_id
    assert artifact_dir.exists() is True

    assert client.chunk_calls == 1

    processed = await service.process_next_pending(app_with_db.state.session_factory)
    assert processed is True

    detail_response = await initialized_client.get(f"/api/v1/style-analysis-jobs/{job_id}")
    detail = detail_response.json()
    assert detail["status"] == "succeeded"
    assert detail["error_message"] is None
    assert client.chunk_calls == 1
    assert client.report_calls == 2
    assert artifact_dir.exists() is False


@pytest.mark.asyncio
async def test_run_claimed_job_emits_periodic_heartbeat_during_long_stage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STYLE_ANALYSIS_STALE_TIMEOUT_SECONDS", "1")
    get_settings.cache_clear()

    service = StyleAnalysisWorkerService()
    touched_stages: list[str | None] = []

    async def fake_load_run_context(session_factory, job_id: str) -> StyleAnalysisRunContext:
        del session_factory, job_id
        return StyleAnalysisRunContext(
            provider=SimpleNamespace(),  # type: ignore[arg-type]
            style_name="心跳任务",
            model_name="gpt-4.1-mini",
            source_filename="sample.txt",
            chunk_count=1,
            classification={
                "text_type": "章节正文",
                "has_timestamps": False,
                "has_speaker_labels": False,
                "has_noise_markers": False,
                "uses_batch_processing": False,
                "location_indexing": "章节或段落位置",
            },
        )

    async def fake_touch_job_stage(session_factory, job_id: str, *, stage: str | None) -> None:
        del session_factory, job_id
        touched_stages.append(stage)

    async def fake_build_pipeline(
        *,
        provider,
        model_name: str,
        style_name: str,
        source_filename: str,
        stage_callback,
    ):
        del provider, model_name, style_name, source_filename

        class FakePipeline:
            async def run(
                self,
                *,
                job_id: str,
                chunk_count: int,
                classification: dict,
                max_concurrency: int,
            ) -> StyleAnalysisPipelineResult:
                del job_id, chunk_count, classification, max_concurrency
                await stage_callback("analyzing_chunks")
                await asyncio.sleep(0.8)
                return StyleAnalysisPipelineResult(
                    analysis_meta=AnalysisMeta(
                        source_filename="sample.txt",
                        model_name="gpt-4.1-mini",
                        text_type="章节正文",
                        has_timestamps=False,
                        has_speaker_labels=False,
                        has_noise_markers=False,
                        uses_batch_processing=False,
                        location_indexing="章节或段落位置",
                        chunk_count=1,
                    ),
                    analysis_report=AnalysisReport.model_validate(build_fake_analysis_report()),
                    style_summary=StyleSummary.model_validate(build_fake_style_summary("心跳任务")),
                    prompt_pack=PromptPack.model_validate(build_fake_prompt_pack()),
                )

        return FakePipeline()

    async def fake_mark_job_succeeded(session_factory, job_id: str, *, result) -> None:
        del session_factory, job_id, result

    async def fake_cleanup_job_artifacts(job_id: str) -> None:
        del job_id

    async def fake_delete_checkpointer_thread(job_id: str) -> None:
        del job_id

    monkeypatch.setattr(service, "_load_run_context", fake_load_run_context)
    monkeypatch.setattr(service, "_touch_job_stage", fake_touch_job_stage)
    monkeypatch.setattr(service, "_build_pipeline", fake_build_pipeline)
    monkeypatch.setattr(service, "_mark_job_succeeded", fake_mark_job_succeeded)
    monkeypatch.setattr(service.storage_service, "cleanup_job_artifacts", fake_cleanup_job_artifacts)
    monkeypatch.setattr(service, "_delete_checkpointer_thread", fake_delete_checkpointer_thread)

    await service._run_claimed_job(SimpleNamespace(), "job-heartbeat")

    analyzing_heartbeats = [stage for stage in touched_stages if stage == "analyzing_chunks"]
    assert len(analyzing_heartbeats) >= 2
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_run_worker_uses_backoff_polling_and_resets_after_processing(
    app_with_db: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = StyleAnalysisWorkerService()
    results = iter([False, False, True, False])
    sleep_calls: list[float] = []

    async def fake_process_next_pending(session_factory) -> bool:
        del session_factory
        try:
            return next(results)
        except StopIteration as exc:
            raise asyncio.CancelledError() from exc

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    monkeypatch.setattr(service, "process_next_pending", fake_process_next_pending)
    monkeypatch.setattr("app.services.style_analysis_worker.asyncio.sleep", fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        await service.run_worker(
            app_with_db.state.session_factory,
            poll_interval_seconds=1.0,
            max_poll_interval_seconds=4.0,
        )

    assert sleep_calls == [1.0, 2.0, 1.0]


@pytest.mark.asyncio
async def test_worker_entrypoint_delegates_polling_to_service_run_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.worker as worker_module

    calls: dict[str, object] = {}

    class FakeEngine:
        def __init__(self) -> None:
            self.dispose_calls = 0

        async def dispose(self) -> None:
            self.dispose_calls += 1

    class FakeService:
        def __init__(self) -> None:
            self.aclose_calls = 0

        async def run_worker(
            self,
            session_factory,
            *,
            poll_interval_seconds: float,
            max_poll_interval_seconds: float | None = None,
        ) -> None:
            calls["session_factory"] = session_factory
            calls["poll_interval_seconds"] = poll_interval_seconds
            calls["max_poll_interval_seconds"] = max_poll_interval_seconds

        async def aclose(self) -> None:
            self.aclose_calls += 1

    fake_engine = FakeEngine()
    fake_service = FakeService()
    fake_session_factory = object()
    settings = SimpleNamespace(
        style_analysis_worker_enabled=True,
        database_url="sqlite+aiosqlite:///./test.db",
        style_analysis_poll_interval_seconds=1.5,
        style_analysis_stale_timeout_seconds=30,
    )

    monkeypatch.setattr(worker_module, "get_settings", lambda: settings)
    monkeypatch.setattr(worker_module, "create_engine", lambda database_url: fake_engine)
    monkeypatch.setattr(worker_module, "create_session_factory", lambda engine: fake_session_factory)
    monkeypatch.setattr(worker_module, "StyleAnalysisWorkerService", lambda: fake_service)

    await worker_module.run_worker()

    assert calls == {
        "session_factory": fake_session_factory,
        "poll_interval_seconds": 1.5,
        "max_poll_interval_seconds": 6.0,
    }
    assert fake_service.aclose_calls == 1
    assert fake_engine.dispose_calls == 1


def test_build_job_detail_response_uses_mapper_bundle(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.style_analysis_jobs import build_job_detail_response

    now = datetime.now(UTC)
    parsed_report = AnalysisReport.model_validate(build_fake_analysis_report())
    parsed_summary = StyleSummary.model_validate(build_fake_style_summary("映射入口"))
    parsed_prompt_pack = PromptPack.model_validate(build_fake_prompt_pack())

    def fake_build_job_result_bundle(job):
        del job
        return None, parsed_report, parsed_summary, parsed_prompt_pack

    monkeypatch.setattr(
        "app.services.style_analysis_jobs.build_job_result_bundle",
        fake_build_job_result_bundle,
    )

    job = SimpleNamespace(
        id="job-1",
        style_name="映射入口",
        provider_id="provider-1",
        model_name="gpt-4.1-mini",
        status="succeeded",
        stage=None,
        error_message=None,
        started_at=now,
        completed_at=now,
        created_at=now,
        updated_at=now,
        provider=SimpleNamespace(
            id="provider-1",
            label="Primary Gateway",
            base_url="https://api.openai.com/v1",
            default_model="gpt-4.1-mini",
            is_enabled=True,
        ),
        sample_file=SimpleNamespace(
            id="sample-1",
            original_filename="sample.txt",
            content_type="text/plain",
            byte_size=12,
            character_count=12,
            checksum_sha256="abc123",
            created_at=now,
            updated_at=now,
        ),
        style_profile=None,
        style_profile_id=None,
        analysis_meta_payload=None,
        analysis_report_payload={"invalid": "payload"},
        style_summary_payload={"invalid": "payload"},
        prompt_pack_payload={"invalid": "payload"},
    )

    response = build_job_detail_response(job)

    assert response.analysis_report == parsed_report
    assert response.style_summary == parsed_summary
    assert response.prompt_pack == parsed_prompt_pack


@pytest.mark.asyncio
async def test_create_app_disposes_owned_engine_on_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeEngine:
        def __init__(self) -> None:
            self.dispose_calls = 0

        async def dispose(self) -> None:
            self.dispose_calls += 1

    class FakeWorkerService:
        async def fail_stale_running_jobs(self, session_factory, *, stale_after_seconds: int) -> None:
            del session_factory, stale_after_seconds

        async def aclose(self) -> None:
            return None

    fake_engine = FakeEngine()
    monkeypatch.setattr("app.main.create_engine", lambda database_url: fake_engine)
    monkeypatch.setattr("app.main.create_session_factory", lambda engine: "fake-session-factory")
    monkeypatch.setattr("app.main.StyleAnalysisWorkerService", lambda: FakeWorkerService())

    app = create_app()
    async with LifespanManager(app):
        pass

    assert fake_engine.dispose_calls == 1


@pytest.mark.asyncio
async def test_style_analysis_job_table_has_hot_path_indexes(
    app_with_db: FastAPI,
) -> None:
    async with app_with_db.state.session_factory() as session:
        connection = await session.connection()
        indexes = await connection.run_sync(
            lambda sync_conn: sa_inspect(sync_conn).get_indexes("style_analysis_jobs")
        )
    index_names = {item["name"] for item in indexes}
    assert "ix_style_analysis_jobs_status_attempt_count_created_at" in index_names
    assert "ix_style_analysis_jobs_status_last_heartbeat_at" in index_names
