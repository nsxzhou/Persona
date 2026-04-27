from __future__ import annotations

from collections.abc import Awaitable, Callable
from types import SimpleNamespace

import pytest
from langgraph.checkpoint.memory import InMemorySaver


class StubLLM:
    def __init__(self, outputs: list[str]) -> None:
        self._outputs = list(outputs)
        self.calls: list[dict[str, str]] = []

    async def __call__(
        self,
        *,
        system_prompt: str,
        user_context: str,
        mode: str,
    ) -> str:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_context": user_context,
                "mode": mode,
            }
        )
        if not self._outputs:
            raise AssertionError("stub llm exhausted")
        return self._outputs.pop(0)


@pytest.mark.asyncio
async def test_project_bootstrap_pipeline_pauses_for_outline_review_and_resumes(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    from app.core.config import get_settings
    from app.services.novel_workflow_pipeline import (
        NovelWorkflowAwaitingHuman,
        NovelWorkflowPipeline,
    )
    from app.services.novel_workflow_storage import NovelWorkflowStorageService

    get_settings.cache_clear()
    decisions: dict[str, dict[str, str]] = {}
    llm = StubLLM(
        [
            "## 第一阶段：入局\n- 主驱动轴：权力扩张",
            "## 世界设定\n- 阶层压制",
            "## 沈砚\n- 角色功能：破局者",
            "## 第一卷：死局入门\n### 第1章：醒在死牢",
            "## 沈砚\n- 当前位置与处境：死牢",
            "## 时间线\n- 第一天：醒在死牢",
            "## 活跃伏笔\n- 案卷里的第二个名字",
        ]
    )
    storage = NovelWorkflowStorageService()
    pipeline = NovelWorkflowPipeline(
        llm_complete=llm,
        storage_service=storage,
        checkpointer=InMemorySaver(),
        decision_loader=lambda run_id: decisions.get(run_id),
    )
    initial_state = {
        "intent_type": "project_bootstrap",
        "project_id": "project-1",
        "project_name": "测试项目",
        "project_description": "一个寒门书生被迫冒名入局。",
        "length_preset": "long",
        "style_prompt": "# Style Prompt\n冷白短句\n",
        "plot_prompt": "# Plot Prompt\n核心驱动轴：身份逆转\n",
            "generation_profile": {
                "genre_mother": "historical_power",
                "intensity_level": "edge",
                "pov_mode": "limited_third",
                "morality_axis": "gray_pragmatism",
                "pace_density": "fast",
            "target_market": "mainstream",
            "desire_overlays": [],
        },
        "current_bible": {
            "world_building": "",
            "characters_blueprint": "",
            "outline_master": "",
            "outline_detail": "",
            "characters_status": "",
            "runtime_state": "",
            "runtime_threads": "",
            "story_summary": "",
        },
    }

    with pytest.raises(NovelWorkflowAwaitingHuman) as exc_info:
        await pipeline.run(run_id="run-project-bootstrap", initial_state=initial_state)

    assert exc_info.value.checkpoint_kind == "outline_bundle"
    bundle = await storage.read_stage_markdown_artifact(
        "run-project-bootstrap",
        name="outline_bundle",
    )
    assert "## outline_master" in bundle
    assert "## world_building" in bundle
    assert "## outline_detail" in bundle

    decisions["run-project-bootstrap"] = {
        "action": "approve",
        "artifact_name": "outline_bundle",
    }
    result = await pipeline.run(run_id="run-project-bootstrap", initial_state=initial_state)

    assert result.checkpoint_kind is None
    assert result.persist_payload["project_bible"]["outline_master"].startswith("## 第一阶段")
    assert result.persist_payload["project_bible"]["world_building"].startswith("## 世界设定")
    assert result.persist_payload["project_bible"]["story_summary"] == ""
    assert "outline_bundle" in result.latest_artifacts


@pytest.mark.asyncio
async def test_chapter_write_pipeline_retries_failed_continuity_before_persisting(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    from app.core.config import get_settings
    from app.services.novel_workflow_pipeline import (
        NovelWorkflowAwaitingHuman,
        NovelWorkflowPipeline,
    )
    from app.services.novel_workflow_storage import NovelWorkflowStorageService

    get_settings.cache_clear()
    decisions: dict[str, dict[str, str]] = {}
    llm = StubLLM(
        [
            "[压抑→试探] 沈砚借验尸官的手套遮住镣铐磨出的血痕\n[悬念→反压] 狱卒提起案卷里多出的名字",
                "第一版正文，出现了与设定冲突的伤势细节。",
                "## Verdict\nfail\n\n## Conflicts\n- 伤势与 runtime_state 冲突\n\n## Character Drift\n- 无\n\n## World Rule Issues\n- 无\n\n## Required Rewrites\n- 去掉错误伤势",
                "第二版正文，伤势细节已修正。",
                "## Verdict\npass\n\n## Conflicts\n- 无\n\n## Character Drift\n- 无\n\n## World Rule Issues\n- 无\n\n## Required Rewrites\n- 无",
                "第二拍正文，狱卒点出案卷中的第二个名字。",
                "## Verdict\npass\n\n## Conflicts\n- 无\n\n## Character Drift\n- 无\n\n## World Rule Issues\n- 无\n\n## Required Rewrites\n- 无",
                "## Verdict\npass\n\n## Conflicts\n- 无\n\n## Character Drift\n- 无\n\n## World Rule Issues\n- 无\n\n## Required Rewrites\n- 无",
                "润色后的正文终稿。",
                "## 角色动态状态\n\n## 沈砚\n- 当前位置与处境：死牢中稳住局面\n\n## 运行时状态\n\n- 沈砚确认案卷存在第二个名字\n\n## 伏笔与线索追踪\n\n- 第二个名字的真实身份仍未揭晓",
                "这一章里，沈砚先稳住狱中局势，再确认案卷中多出的名字，为越狱与翻案埋下新钩子。",
            "## 全局故事摘要 (GLOBAL_SUMMARY_UPDATED)\n\n### 情节发展\n- 沈砚确认案卷里另有其名。",
        ]
    )
    storage = NovelWorkflowStorageService()
    pipeline = NovelWorkflowPipeline(
        llm_complete=llm,
        storage_service=storage,
        checkpointer=InMemorySaver(),
        decision_loader=lambda run_id: decisions.get(run_id),
    )
    initial_state = {
        "intent_type": "chapter_write",
        "project_id": "project-1",
        "chapter_id": "chapter-1",
        "project_name": "测试项目",
        "project_description": "一个寒门书生被迫冒名入局。",
        "length_preset": "long",
        "style_prompt": "# Style Prompt\n冷白短句\n",
        "plot_prompt": "# Plot Prompt\n核心驱动轴：身份逆转\n",
            "generation_profile": {
                "genre_mother": "historical_power",
                "intensity_level": "edge",
                "pov_mode": "limited_third",
                "morality_axis": "gray_pragmatism",
                "pace_density": "fast",
            "target_market": "mainstream",
            "desire_overlays": [],
        },
        "current_bible": {
            "world_building": "## 世界设定\n- 死牢森严",
            "characters_blueprint": "## 沈砚\n- 主角",
            "outline_master": "## 第一阶段：入局",
            "outline_detail": "### 第1章：醒在死牢",
            "characters_status": "## 沈砚\n- 位置：死牢",
            "runtime_state": "- 沈砚刚醒来",
            "runtime_threads": "- 第二个名字未解",
            "story_summary": "## 全局故事摘要\n- 旧进展",
        },
        "chapter_snapshot": {
            "title": "第1章：醒在死牢",
            "content": "",
            "summary": "",
            "beats_markdown": "",
        },
        "text_before_cursor": "",
        "current_chapter_context": "**第1章：醒在死牢**\n- 核心事件：确认死局",
        "previous_chapter_context": "",
        "total_content_length": 0,
        "enable_editor_pass": True,
    }

    with pytest.raises(NovelWorkflowAwaitingHuman) as exc_info:
        await pipeline.run(run_id="run-chapter-write", initial_state=initial_state)
    assert exc_info.value.checkpoint_kind == "beats"

    beats_artifact = await storage.read_stage_markdown_artifact(
        "run-chapter-write",
        name="beats_markdown",
    )
    assert "压抑→试探" in beats_artifact

    decisions["run-chapter-write"] = {
        "action": "approve",
        "artifact_name": "beats_markdown",
    }
    result = await pipeline.run(run_id="run-chapter-write", initial_state=initial_state)

    assert result.persist_payload["chapter"]["content"] == "润色后的正文终稿。"
    assert result.persist_payload["chapter"]["beats_markdown"] == beats_artifact
    assert result.persist_payload["chapter"]["summary"].startswith("这一章里")
    assert result.persist_payload["project_bible"]["runtime_state"].startswith("- 沈砚确认")
    assert result.persist_payload["project_bible"]["story_summary"].startswith("## 全局故事摘要")
    assert result.warnings == []
