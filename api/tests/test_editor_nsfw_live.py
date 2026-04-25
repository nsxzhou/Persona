from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select

from app.services.context_assembly import (
    WritingContextSections,
    assemble_writing_context,
)

pytestmark = pytest.mark.live_llm

_STYLE_PROMPT_PACK = """# System Prompt
你是一名中文男频网文作者。

## 文风要求
- 句子偏短，节奏紧。
- 情绪张力优先通过动作、距离、停顿和潜台词呈现。
- 直接输出正文，不要解释。
"""

_PLOT_PROMPT_PACK = """# Shared Constraints
- 本书主驱动轴：关系张力 + 资源突破。
- 读者追读问题：这次男女双修会不会真正改变两人的关系与力量结构。
- 压制后兑现，兑现后反噬。

# Continuation Guardrails
- 保留成年人之间的危险吸引、身份差、利益交换、暧昧推拉、嫉妒、误会和禁忌氛围。
- 重点写成年男修与成年女修之间的关系试探、边界变化、双修突破代价与后续尴尬。
- 不要只写气氛，必须让局面推进。
"""


def _collect_sse_data(raw: str) -> str:
    chunks: list[str] = []
    for line in raw.splitlines():
        if line.startswith("data: "):
            payload = line[6:].strip()
            if payload:
                chunks.append(json.loads(payload))
    return "".join(chunks)


_SUBTLE_INTIMACY_CUES = (
    "呼吸",
    "体温",
    "气息",
    "心跳",
    "视线",
    "眼神",
    "掌心",
    "指尖",
    "手背",
    "腰背",
    "衣袖",
    "发丝",
    "靠近",
    "贴近",
)


@pytest.mark.asyncio
async def test_editor_completion_prints_output_using_builtin_plot_contract_without_legacy_abstraction(
    initialized_live_client: AsyncClient,
    initialized_live_provider: dict[str, object],
    app_with_db: FastAPI,
) -> None:
    from app.db.models import (
        PlotAnalysisJob,
        PlotProfile,
        PlotSampleFile,
        Project,
        ProjectBible,
        StyleAnalysisJob,
        StyleProfile,
        StyleSampleFile,
    )

    provider_id = str(initialized_live_provider["id"])
    default_model = str(initialized_live_provider["default_model"])

    built_system_prompt = assemble_writing_context(
        _STYLE_PROMPT_PACK,
        plot_prompt=_PLOT_PROMPT_PACK,
        sections=WritingContextSections(
            description="成年男修与成年女修双修场景实验",
            outline_detail="一名成年男修与一名成年女修在闭关中尝试双修，关系与突破同步推进。",
            runtime_state="成年男修与成年女修互有情意，但没有明确越界。",
            runtime_threads="若男女双修成功，关系会从试探进入默认绑定。",
        ),
        length_preset="short",
        content_length=1200,
    )
    assert "Plot 指纹落地契约" in built_system_prompt
    assert "成年人的关系张力优先通过身份差、利益交换、名分压力、嫉妒误会、暧昧推拉，以及呼吸、体温、气息、视线停顿、心跳失衡、掌心温度、衣料摩擦、手背/腰背/衣袖/发丝接触等隐晦身体与感官暗示呈现" in built_system_prompt

    create_project_response = await initialized_live_client.post(
        "/api/v1/projects",
        json={
            "name": "Built-in Plot Contract Probe",
            "description": "验证项目内置 Plot 指纹落地契约参与正文生成，且不带 legacy abstraction。",
            "status": "draft",
            "default_provider_id": provider_id,
            "default_model": default_model,
            "style_profile_id": None,
            "plot_profile_id": None,
            "length_preset": "short",
            "auto_sync_memory": False,
        },
    )
    assert create_project_response.status_code == 201
    project_id = create_project_response.json()["id"]

    async with app_with_db.state.session_factory() as session:
        project = await session.scalar(select(Project).where(Project.id == project_id))
        assert project is not None
        bible = await session.scalar(
            select(ProjectBible).where(ProjectBible.project_id == project_id)
        )
        assert bible is not None

        project.description = "成人关系张力仙侠实验，观察项目内置 Plot 指纹契约如何影响正文续写。"
        bible.outline_detail = (
            "本章目标：一名成年男修与一名成年女修在密室闭关中尝试双修，"
            "重点写灵力共振、关系试探、双修突破代价和后续尴尬。"
        )
        bible.runtime_state = "成年男修与成年女修互有情愫，但仍保持克制，没有真正越界。"
        bible.runtime_threads = "若此次男女双修成功，两人的关系会进入新的默认默契。"

        style_sample_file = StyleSampleFile(
            user_id=project.user_id,
            original_filename="style-probe.txt",
            content_type="text/plain",
            storage_path="temp/style-probe.txt",
            byte_size=16,
            character_count=16,
            checksum_sha256="1" * 64,
        )
        session.add(style_sample_file)
        await session.flush()

        style_job = StyleAnalysisJob(
            user_id=project.user_id,
            style_name="内置 Prompt 实验风格",
            provider_id=project.default_provider_id,
            model_name=project.default_model,
            sample_file_id=style_sample_file.id,
            status="succeeded",
            analysis_report_payload="# 执行摘要\n用于挂载临时 style prompt。\n",
            style_summary_payload="# 风格名称\n内置 Prompt 实验风格\n",
            prompt_pack_payload=_STYLE_PROMPT_PACK,
        )
        session.add(style_job)
        await session.flush()

        style_profile = StyleProfile(
            user_id=project.user_id,
            source_job_id=style_job.id,
            provider_id=project.default_provider_id,
            model_name=project.default_model,
            source_filename=style_sample_file.original_filename,
            style_name="内置 Prompt 实验风格",
            analysis_report_payload="# 执行摘要\n用于挂载临时 style prompt。\n",
            style_summary_payload="# 风格名称\n内置 Prompt 实验风格\n",
            prompt_pack_payload=_STYLE_PROMPT_PACK,
        )
        session.add(style_profile)
        await session.flush()

        plot_sample_file = PlotSampleFile(
            user_id=project.user_id,
            original_filename="plot-probe.txt",
            content_type="text/plain",
            storage_path="temp/plot-probe.txt",
            byte_size=16,
            character_count=16,
            checksum_sha256="2" * 64,
        )
        session.add(plot_sample_file)
        await session.flush()

        plot_job = PlotAnalysisJob(
            user_id=project.user_id,
            plot_name="内置 Plot Contract 实验",
            provider_id=project.default_provider_id,
            model_name=project.default_model,
            sample_file_id=plot_sample_file.id,
            status="succeeded",
            analysis_report_payload="# 执行摘要\n用于挂载临时 plot prompt。\n",
            plot_summary_payload="# Plot Summary\n关系张力与突破绑定。\n",
            prompt_pack_payload=_PLOT_PROMPT_PACK,
            plot_skeleton_payload="# 全书骨架\n启动期\n",
        )
        session.add(plot_job)
        await session.flush()

        plot_profile = PlotProfile(
            user_id=project.user_id,
            source_job_id=plot_job.id,
            provider_id=project.default_provider_id,
            model_name=project.default_model,
            source_filename=plot_sample_file.original_filename,
            plot_name="内置 Plot Contract 实验",
            analysis_report_payload="# 执行摘要\n用于挂载临时 plot prompt。\n",
            plot_summary_payload="# Plot Summary\n关系张力与突破绑定。\n",
            prompt_pack_payload=_PLOT_PROMPT_PACK,
            plot_skeleton_payload="# 全书骨架\n启动期\n",
        )
        session.add(plot_profile)
        await session.flush()

        project.style_profile_id = style_profile.id
        project.plot_profile_id = plot_profile.id
        await session.commit()

    payload = {
        "previous_chapter_context": "上一章末尾，成年男修与成年女修已经约定尝试双修，但谁都没有把话说透。",
        "current_chapter_context": "静室封闭，外界无人打扰，当前唯一目标是让这一场男女双修冲开瓶颈。",
        "text_before_cursor": "双修阵法已起，四壁静得只剩呼吸与烛火，女修把手按在阵心，示意那名男修过来。",
        "total_content_length": 1200,
    }

    async with initialized_live_client.stream(
        "POST",
        f"/api/v1/projects/{project_id}/editor/complete",
        json=payload,
    ) as response:
        raw = "".join([chunk async for chunk in response.aiter_text()])

    assert response.status_code == 200, raw
    assert "event: error" not in raw, raw

    text = _collect_sse_data(raw)
    assert text.strip()
    assert any(cue in text for cue in _SUBTLE_INTIMACY_CUES), text

    output_path = (
        Path(__file__).resolve().parents[2]
        / "temp"
        / "builtin_plot_contract_completion_output.md"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")

    print("\n=== LLM RAW OUTPUT START ===\n")
    print(text)
    print("\n=== LLM RAW OUTPUT END ===\n")
    print(f"Saved raw output to: {output_path}")
