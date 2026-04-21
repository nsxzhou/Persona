from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select

from app.api.assemblers import build_plot_profile_result_bundle
from app.core.config import get_settings
from app.db.models import PlotAnalysisJob, PlotProfile, PlotSampleFile, Project
from app.services.plot_analysis_jobs import PlotAnalysisJobService
from app.services.plot_analysis_storage import PlotAnalysisStorageService


def build_fake_plot_report() -> str:
    return "# 执行摘要\n这本书靠高压绑定、反截胡与关系失衡推进。\n"


def build_fake_plot_summary(plot_name: str) -> str:
    return f"# 剧情定位\n{plot_name}\n\n# 读者追读抓手\n高压绑定 + 反派求生。\n"


def build_fake_plot_prompt_pack() -> str:
    return (
        "# Shared Constraints\n- 保持高压绑定开局\n\n"
        "# Outline Master Prompt\n按高压绑定推进总纲。\n"
    )


def build_fake_plot_skeleton() -> str:
    return (
        "# 全书骨架\n\n"
        "## 主角线\n高压绑定 → 反截胡 → 关系失衡收束。\n\n"
        "## 阶段节奏\n开局-推进-反转-收束。\n"
    )


async def create_succeeded_plot_job(
    *,
    initialized_client: AsyncClient,
    app_with_db: FastAPI,
    provider_id: str,
    model_name: str,
    plot_name: str,
) -> tuple[str, dict[str, str]]:
    create_job_response = await initialized_client.post(
        "/api/v1/plot-analysis-jobs",
        data={"plot_name": plot_name, "provider_id": provider_id},
        files={"file": ("sample.txt", "第一章 风雪夜归人".encode("utf-8"), "text/plain")},
    )
    assert create_job_response.status_code == 201
    job_id = create_job_response.json()["id"]

    detail = {
        "analysis_report_markdown": build_fake_plot_report(),
        "plot_summary_markdown": build_fake_plot_summary(plot_name),
        "prompt_pack_markdown": build_fake_plot_prompt_pack(),
        "plot_skeleton_markdown": build_fake_plot_skeleton(),
    }

    async with app_with_db.state.session_factory() as session:
        await PlotAnalysisJobService().mark_job_succeeded(
            session,
            job_id,
            analysis_meta_payload={
                "source_filename": "sample.txt",
                "model_name": model_name,
                "text_type": "章节正文",
                "has_timestamps": False,
                "has_speaker_labels": False,
                "has_noise_markers": False,
                "uses_batch_processing": False,
                "location_indexing": "章节或段落位置",
                "chunk_count": 1,
            },
            analysis_report_payload=detail["analysis_report_markdown"],
            plot_summary_payload=detail["plot_summary_markdown"],
            prompt_pack_payload=detail["prompt_pack_markdown"],
            plot_skeleton_payload=detail["plot_skeleton_markdown"],
        )
        await session.commit()

    return job_id, detail


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
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    job_id, detail = await create_succeeded_plot_job(
        initialized_client=initialized_client,
        app_with_db=app_with_db,
        plot_name="反派修罗场推进模板",
        provider_id=provider_id,
        model_name=str(initialized_provider["default_model"]),
    )

    create_profile_response = await initialized_client.post(
        "/api/v1/plot-profiles",
        json={
            "job_id": job_id,
            "plot_name": "反派修罗场推进模板（修订版）",
            "mount_project_id": project_id,
            "plot_summary_markdown": detail["plot_summary_markdown"] + "\n# 生成禁区\n不要洗白主角\n",
            "prompt_pack_markdown": "## 修订版\n" + detail["prompt_pack_markdown"],
        },
    )

    assert create_profile_response.status_code == 201
    profile = create_profile_response.json()
    assert profile["plot_name"] == "反派修罗场推进模板（修订版）"
    assert profile["source_job_id"] == job_id
    assert profile["provider_id"] == provider_id
    assert profile["source_filename"] == "sample.txt"
    assert profile["analysis_report_markdown"].startswith("# 执行摘要")
    assert "不要洗白主角" in profile["plot_summary_markdown"]
    assert profile["prompt_pack_markdown"].startswith("## 修订版")
    async with app_with_db.state.session_factory() as session:
        project = await session.scalar(select(Project).where(Project.id == project_id))
        assert project is not None
        assert project.plot_profile_id == profile["id"]

    second_project_response = await initialized_client.post(
        "/api/v1/projects",
        json={
            "name": "情节挂载项目 2",
            "description": "用于验证更新时重新挂载",
            "status": "draft",
            "default_provider_id": provider_id,
            "default_model": "",
            "style_profile_id": None,
            "plot_profile_id": None,
        },
    )
    assert second_project_response.status_code == 201
    second_project_id = second_project_response.json()["id"]

    update_profile_response = await initialized_client.patch(
        f"/api/v1/plot-profiles/{profile['id']}",
        json={
            "plot_name": "反派修罗场推进模板（终版）",
            "mount_project_id": second_project_id,
            "plot_summary_markdown": "# 剧情定位\n反派修罗场推进模板（终版）\n",
            "prompt_pack_markdown": "# Shared Constraints\n终版 Prompt\n",
        },
    )
    assert update_profile_response.status_code == 200
    updated_profile = update_profile_response.json()
    assert updated_profile["plot_name"] == "反派修罗场推进模板（终版）"
    assert updated_profile["plot_summary_markdown"].startswith("# 剧情定位")
    assert updated_profile["prompt_pack_markdown"] == "# Shared Constraints\n终版 Prompt\n"
    async with app_with_db.state.session_factory() as session:
        second_project = await session.scalar(select(Project).where(Project.id == second_project_id))
        assert second_project is not None
        assert second_project.plot_profile_id == profile["id"]

    detail_response = await initialized_client.get(f"/api/v1/plot-profiles/{profile['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == profile["id"]

    job_detail_response = await initialized_client.get(f"/api/v1/plot-analysis-jobs/{job_id}")
    assert job_detail_response.status_code == 200
    assert job_detail_response.json()["plot_profile"]["id"] == profile["id"]


@pytest.mark.asyncio
async def test_create_plot_profile_rolls_back_when_mount_project_is_missing(
    initialized_client: AsyncClient,
    app_with_db: FastAPI,
    initialized_provider: dict[str, object],
) -> None:
    job_id, detail = await create_succeeded_plot_job(
        initialized_client=initialized_client,
        app_with_db=app_with_db,
        plot_name="事务校验情节模板",
        provider_id=str(initialized_provider["id"]),
        model_name=str(initialized_provider["default_model"]),
    )

    create_profile_response = await initialized_client.post(
        "/api/v1/plot-profiles",
        json={
            "job_id": job_id,
            "plot_name": "事务校验情节模板",
            "mount_project_id": "missing-project",
            "plot_summary_markdown": detail["plot_summary_markdown"],
            "prompt_pack_markdown": detail["prompt_pack_markdown"],
        },
    )

    assert create_profile_response.status_code == 404
    assert create_profile_response.json()["detail"] == "项目不存在"
    async with app_with_db.state.session_factory() as session:
        profile = await session.scalar(select(PlotProfile).where(PlotProfile.source_job_id == job_id))
        assert profile is None


@pytest.mark.asyncio
async def test_delete_plot_profile_rejects_when_mounted_to_project(
    initialized_client: AsyncClient,
    app_with_db: FastAPI,
    initialized_provider: dict[str, object],
) -> None:
    provider_id = str(initialized_provider["id"])
    project_response = await initialized_client.post(
        "/api/v1/projects",
        json={
            "name": "挂载中的情节项目",
            "description": "验证删除保护",
            "status": "draft",
            "default_provider_id": provider_id,
            "default_model": "",
            "style_profile_id": None,
            "plot_profile_id": None,
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    job_id, detail = await create_succeeded_plot_job(
        initialized_client=initialized_client,
        app_with_db=app_with_db,
        plot_name="删除保护情节模板",
        provider_id=provider_id,
        model_name=str(initialized_provider["default_model"]),
    )

    create_profile_response = await initialized_client.post(
        "/api/v1/plot-profiles",
        json={
            "job_id": job_id,
            "plot_name": "删除保护情节模板",
            "mount_project_id": project_id,
            "plot_summary_markdown": detail["plot_summary_markdown"],
            "prompt_pack_markdown": detail["prompt_pack_markdown"],
        },
    )
    assert create_profile_response.status_code == 201
    profile_id = create_profile_response.json()["id"]

    delete_response = await initialized_client.delete(f"/api/v1/plot-profiles/{profile_id}")
    assert delete_response.status_code == 409
    assert delete_response.json()["detail"] == "该情节档案正被项目引用，无法删除"


@pytest.mark.asyncio
async def test_delete_plot_analysis_job_removes_saved_profile_and_sample_file(
    initialized_client: AsyncClient,
    app_with_db: FastAPI,
    initialized_provider: dict[str, object],
) -> None:
    provider_id = str(initialized_provider["id"])
    create_job_response = await initialized_client.post(
        "/api/v1/plot-analysis-jobs",
        data={"plot_name": "删除任务情节模板", "provider_id": provider_id},
        files={"file": ("sample.txt", "第一章 风雪夜归人".encode("utf-8"), "text/plain")},
    )
    assert create_job_response.status_code == 201
    job = create_job_response.json()
    job_id = job["id"]
    sample_file_id = job["sample_file"]["id"]

    storage_service = PlotAnalysisStorageService()
    sample_file_path = Path(get_settings().storage_dir) / "plot-samples" / f"{sample_file_id}.txt"
    await storage_service.write_chunk_artifact(job_id, 0, "中间产物")
    artifact_dir = Path(get_settings().storage_dir) / "plot-analysis-artifacts" / job_id
    assert sample_file_path.exists() is True
    assert artifact_dir.exists() is True

    async with app_with_db.state.session_factory() as session:
        db_job = await session.scalar(
            select(PlotAnalysisJob).where(PlotAnalysisJob.id == job_id)
        )
        assert db_job is not None
        db_job.status = "succeeded"
        db_job.analysis_report_payload = build_fake_plot_report()
        db_job.plot_summary_payload = build_fake_plot_summary("删除任务情节模板")
        db_job.prompt_pack_payload = build_fake_plot_prompt_pack()
        db_job.analysis_meta_payload = {
            "source_filename": "sample.txt",
            "model_name": str(initialized_provider["default_model"]),
            "text_type": "章节正文",
            "has_timestamps": False,
            "has_speaker_labels": False,
            "has_noise_markers": False,
            "uses_batch_processing": False,
            "location_indexing": "章节或段落位置",
            "chunk_count": 1,
        }
        await session.commit()

    create_profile_response = await initialized_client.post(
        "/api/v1/plot-profiles",
        json={
            "job_id": job_id,
            "plot_name": "删除任务情节模板",
            "plot_summary_markdown": build_fake_plot_summary("删除任务情节模板"),
            "prompt_pack_markdown": build_fake_plot_prompt_pack(),
        },
    )
    assert create_profile_response.status_code == 201

    delete_job_response = await initialized_client.delete(
        f"/api/v1/plot-analysis-jobs/{job_id}"
    )
    assert delete_job_response.status_code == 204
    assert sample_file_path.exists() is False
    assert artifact_dir.exists() is False

    async with app_with_db.state.session_factory() as session:
        assert (
            await session.scalar(select(PlotAnalysisJob).where(PlotAnalysisJob.id == job_id))
        ) is None
        assert (
            await session.scalar(
                select(PlotProfile).where(PlotProfile.source_job_id == job_id)
            )
        ) is None
        assert (
            await session.scalar(
                select(PlotSampleFile).where(PlotSampleFile.id == sample_file_id)
            )
        ) is None


def test_build_plot_profile_result_bundle_only_depends_on_new_payload_fields() -> None:
    analysis_report = build_fake_plot_report()
    plot_summary = build_fake_plot_summary("反派修罗场推进模板")
    prompt_pack = build_fake_plot_prompt_pack()
    profile = SimpleNamespace(
        analysis_report_payload=analysis_report,
        plot_summary_payload=plot_summary,
        prompt_pack_payload=prompt_pack,
    )
    result_report, result_summary, result_prompt_pack = build_plot_profile_result_bundle(profile)
    assert result_report == analysis_report
    assert result_summary == plot_summary
    assert result_prompt_pack == prompt_pack


def test_build_plot_profile_response_payload_includes_skeleton_markdown() -> None:
    from datetime import datetime

    from app.api.assemblers import build_plot_profile_response_payload

    now = datetime.now()
    skeleton = build_fake_plot_skeleton()
    profile = SimpleNamespace(
        id="profile-1",
        source_job_id="job-1",
        provider_id="provider-1",
        model_name="gpt-4.1-mini",
        source_filename="sample.txt",
        plot_name="反派修罗场推进模板",
        analysis_report_payload=build_fake_plot_report(),
        plot_summary_payload=build_fake_plot_summary("反派修罗场推进模板"),
        prompt_pack_payload=build_fake_plot_prompt_pack(),
        plot_skeleton_payload=skeleton,
        created_at=now,
        updated_at=now,
    )
    payload = build_plot_profile_response_payload(profile)
    assert payload["plot_skeleton_markdown"] == skeleton


def test_build_plot_job_detail_response_includes_skeleton_markdown() -> None:
    from datetime import datetime

    from app.api.assemblers import build_plot_job_detail_response

    now = datetime.now()
    skeleton = build_fake_plot_skeleton()
    provider = SimpleNamespace(
        id="provider-1",
        label="provider",
        default_model="gpt-4.1-mini",
        base_url="https://api.example.test/v1",
        is_enabled=True,
    )
    sample_file = SimpleNamespace(
        id="sample-1",
        original_filename="sample.txt",
        content_type="text/plain",
        byte_size=42,
        character_count=100,
        checksum_sha256="abc",
        created_at=now,
        updated_at=now,
    )
    job = SimpleNamespace(
        id="job-1",
        plot_name="反派修罗场推进模板",
        provider_id="provider-1",
        model_name="gpt-4.1-mini",
        status="succeeded",
        stage=None,
        error_message=None,
        started_at=now,
        completed_at=now,
        created_at=now,
        updated_at=now,
        pause_requested_at=None,
        provider=provider,
        sample_file=sample_file,
        plot_profile_id=None,
        plot_profile=None,
        analysis_report_payload=build_fake_plot_report(),
        plot_summary_payload=build_fake_plot_summary("反派修罗场推进模板"),
        prompt_pack_payload=build_fake_plot_prompt_pack(),
        plot_skeleton_payload=skeleton,
    )
    response = build_plot_job_detail_response(job)
    assert response.plot_skeleton_markdown == skeleton


@pytest.mark.asyncio
async def test_get_plot_skeleton_or_409_returns_payload_when_succeeded(
    initialized_client: AsyncClient,
    app_with_db: FastAPI,
    initialized_provider: dict[str, object],
) -> None:
    job_id, detail = await create_succeeded_plot_job(
        initialized_client=initialized_client,
        app_with_db=app_with_db,
        plot_name="骨架读取成功",
        provider_id=str(initialized_provider["id"]),
        model_name=str(initialized_provider["default_model"]),
    )

    async with app_with_db.state.session_factory() as session:
        skeleton = await PlotAnalysisJobService().get_plot_skeleton_or_409(
            session, job_id
        )
    assert skeleton == detail["plot_skeleton_markdown"]


@pytest.mark.asyncio
async def test_get_plot_skeleton_or_409_raises_conflict_when_not_ready(
    initialized_client: AsyncClient,
    app_with_db: FastAPI,
    initialized_provider: dict[str, object],
) -> None:
    from app.core.domain_errors import ConflictError

    create_job_response = await initialized_client.post(
        "/api/v1/plot-analysis-jobs",
        data={
            "plot_name": "骨架未就绪",
            "provider_id": str(initialized_provider["id"]),
        },
        files={"file": ("sample.txt", "第一章 风雪夜归人".encode("utf-8"), "text/plain")},
    )
    assert create_job_response.status_code == 201
    job_id = create_job_response.json()["id"]

    async with app_with_db.state.session_factory() as session:
        with pytest.raises(ConflictError):
            await PlotAnalysisJobService().get_plot_skeleton_or_409(session, job_id)
