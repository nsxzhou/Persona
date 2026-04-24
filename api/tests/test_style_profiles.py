from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select

from app.db.models import Project, StyleProfile
from app.api.assemblers import build_profile_result_bundle


def test_style_profile_service_does_not_import_job_module_helpers() -> None:
    import app.services.style_profiles as style_profiles_module

    source = inspect.getsource(style_profiles_module)
    assert "from app.services.style_analysis_jobs import build_job_result_bundle" not in source


def build_fake_analysis_report() -> str:
    return "# 执行摘要\n整体文风缓慢、潮湿、情绪延迟。\n"


def build_fake_style_summary(style_name: str) -> str:
    return f"# 风格名称\n{style_name}\n\n# 风格定位\n迟滞、潮湿、回望感强。\n"


def build_fake_prompt_pack() -> str:
    return "# System Prompt\n以迟滞、潮湿、回望感强的中文小说文风进行创作。\n"


@pytest.mark.asyncio
@pytest.mark.live_llm
async def test_create_and_update_style_profile_from_succeeded_job_and_mount_project(
    initialized_live_client: AsyncClient,
    app_with_db: FastAPI,
    initialized_live_provider: dict[str, object],
    run_live_style_analysis_job,
) -> None:
    provider_id = str(initialized_live_provider["id"])

    project_response = await initialized_live_client.post(
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

    result = await run_live_style_analysis_job(
        style_name="王家卫风格",
        model=str(initialized_live_provider["default_model"]),
    )
    job_id = result["job"]["id"]
    detail = result["detail"]

    create_profile_response = await initialized_live_client.post(
        "/api/v1/style-profiles",
        json={
            "job_id": job_id,
            "style_name": "王家卫风格（修订版）",
            "mount_project_id": project_id,
            "style_summary_markdown": detail["style_summary_markdown"] + "\n# 备注\n修订版\n",
            "prompt_pack_markdown": "## 修订版\n" + detail["prompt_pack_markdown"],
        },
    )

    assert create_profile_response.status_code == 201
    profile = create_profile_response.json()
    assert profile["style_name"] == "王家卫风格（修订版）"
    assert profile["source_job_id"] == job_id
    assert profile["provider_id"] == provider_id
    assert profile["source_filename"] == "sample.txt"
    assert profile["analysis_report_markdown"].startswith("# 执行摘要")
    assert "修订版" in profile["style_summary_markdown"]
    assert profile["prompt_pack_markdown"].startswith("## 修订版")
    async with app_with_db.state.session_factory() as session:
        project = await session.scalar(select(Project).where(Project.id == project_id))
        assert project is not None
        assert project.style_profile_id == profile["id"]

    second_project_response = await initialized_live_client.post(
        "/api/v1/projects",
        json={
            "name": "风格挂载项目 2",
            "description": "用于验证更新时重新挂载",
            "status": "draft",
            "default_provider_id": provider_id,
            "default_model": "",
            "style_profile_id": None,
        },
    )
    assert second_project_response.status_code == 201
    second_project_id = second_project_response.json()["id"]

    update_profile_response = await initialized_live_client.patch(
        f"/api/v1/style-profiles/{profile['id']}",
        json={
            "style_name": "王家卫风格（终版）",
            "mount_project_id": second_project_id,
            "style_summary_markdown": "# 风格名称\n王家卫风格（终版）\n",
            "prompt_pack_markdown": "# System Prompt\n终版 Prompt\n",
        },
    )
    assert update_profile_response.status_code == 200
    updated_profile = update_profile_response.json()
    assert updated_profile["style_name"] == "王家卫风格（终版）"
    assert updated_profile["style_summary_markdown"].startswith("# 风格名称")
    assert updated_profile["prompt_pack_markdown"] == "# System Prompt\n终版 Prompt\n"
    async with app_with_db.state.session_factory() as session:
        second_project = await session.scalar(select(Project).where(Project.id == second_project_id))
        assert second_project is not None
        assert second_project.style_profile_id == profile["id"]

    detail_response = await initialized_live_client.get(f"/api/v1/style-profiles/{profile['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == profile["id"]

    job_detail_response = await initialized_live_client.get(f"/api/v1/style-analysis-jobs/{job_id}")
    assert job_detail_response.status_code == 200
    assert job_detail_response.json()["style_profile"]["id"] == profile["id"]
    assert job_detail_response.json()["analysis_report_markdown"].startswith("# 执行摘要")
    assert "终版" in job_detail_response.json()["style_summary_markdown"]
    assert job_detail_response.json()["prompt_pack_markdown"].startswith("# System Prompt")


@pytest.mark.asyncio
@pytest.mark.live_llm
async def test_update_profile_keeps_analysis_report_payload_unchanged(
    initialized_live_client: AsyncClient,
    initialized_live_provider: dict[str, object],
    run_live_style_analysis_job,
) -> None:
    result = await run_live_style_analysis_job(
        style_name="王家卫风格",
        model=str(initialized_live_provider["default_model"]),
    )
    job_id = result["job"]["id"]
    detail = result["detail"]

    create_profile_response = await initialized_live_client.post(
        "/api/v1/style-profiles",
        json={
            "job_id": job_id,
            "style_name": "王家卫风格（初版）",
            "style_summary_markdown": detail["style_summary_markdown"],
            "prompt_pack_markdown": detail["prompt_pack_markdown"],
        },
    )
    assert create_profile_response.status_code == 201
    profile = create_profile_response.json()

    update_profile_response = await initialized_live_client.patch(
        f"/api/v1/style-profiles/{profile['id']}",
        json={
            "style_name": "王家卫风格（改）",
            "style_summary_markdown": "# 风格名称\n王家卫风格（改）\n",
            "prompt_pack_markdown": "# System Prompt\n仅更新 prompt_pack payload。\n",
        },
    )
    assert update_profile_response.status_code == 200
    updated_profile = update_profile_response.json()
    assert updated_profile["analysis_report_markdown"] == profile["analysis_report_markdown"]
    assert updated_profile["style_summary_markdown"] == "# 风格名称\n王家卫风格（改）\n"
    assert updated_profile["prompt_pack_markdown"] == "# System Prompt\n仅更新 prompt_pack payload。\n"


def test_build_profile_result_bundle_only_depends_on_new_payload_fields() -> None:
    analysis_report = build_fake_analysis_report()
    style_summary = build_fake_style_summary("王家卫风格（新）")
    prompt_pack = build_fake_prompt_pack()
    profile = SimpleNamespace(
        analysis_report_payload=analysis_report,
        style_summary_payload=style_summary,
        prompt_pack_payload=prompt_pack,
    )
    result_report, result_summary, result_prompt_pack = build_profile_result_bundle(profile)
    assert result_report == analysis_report
    assert result_summary == style_summary
    assert result_prompt_pack == prompt_pack


@pytest.mark.asyncio
@pytest.mark.live_llm
async def test_create_style_profile_rolls_back_when_mount_project_is_missing(
    initialized_live_client: AsyncClient,
    app_with_db: FastAPI,
    initialized_live_provider: dict[str, object],
    run_live_style_analysis_job,
) -> None:
    result = await run_live_style_analysis_job(
        style_name="事务校验风格",
        model=str(initialized_live_provider["default_model"]),
    )
    job_id = result["job"]["id"]
    detail = result["detail"]

    create_profile_response = await initialized_live_client.post(
        "/api/v1/style-profiles",
        json={
            "job_id": job_id,
            "style_name": "事务校验风格",
            "mount_project_id": "missing-project",
            "style_summary_markdown": detail["style_summary_markdown"],
            "prompt_pack_markdown": detail["prompt_pack_markdown"],
        },
    )

    assert create_profile_response.status_code == 404
    assert create_profile_response.json()["detail"] == "项目不存在"
    async with app_with_db.state.session_factory() as session:
        profile = await session.scalar(select(StyleProfile).where(StyleProfile.source_job_id == job_id))
        assert profile is None


@pytest.mark.asyncio
@pytest.mark.live_llm
async def test_delete_style_profile_rejects_when_mounted_to_project(
    initialized_live_client: AsyncClient,
    initialized_live_provider: dict[str, object],
    run_live_style_analysis_job,
) -> None:
    provider_id = str(initialized_live_provider["id"])
    project_response = await initialized_live_client.post(
        "/api/v1/projects",
        json={
            "name": "挂载中的项目",
            "description": "验证删除保护",
            "status": "draft",
            "default_provider_id": provider_id,
            "default_model": "",
            "style_profile_id": None,
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    result = await run_live_style_analysis_job(
        style_name="删除保护风格",
        model=str(initialized_live_provider["default_model"]),
    )
    job_id = result["job"]["id"]
    detail = result["detail"]

    create_profile_response = await initialized_live_client.post(
        "/api/v1/style-profiles",
        json={
            "job_id": job_id,
            "style_name": "删除保护风格",
            "mount_project_id": project_id,
            "style_summary_markdown": detail["style_summary_markdown"],
            "prompt_pack_markdown": detail["prompt_pack_markdown"],
        },
    )
    assert create_profile_response.status_code == 201
    profile_id = create_profile_response.json()["id"]

    delete_response = await initialized_live_client.delete(f"/api/v1/style-profiles/{profile_id}")
    assert delete_response.status_code == 409
    assert delete_response.json()["detail"] == "该风格档案正被项目引用，无法删除"
