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




