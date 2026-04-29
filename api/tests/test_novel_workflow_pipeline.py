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
async def test_selection_rewrite_selects_active_characters_and_includes_selection_context(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    from app.core.config import get_settings
    from app.services.novel_workflow_pipeline import NovelWorkflowPipeline
    from app.services.novel_workflow_storage import NovelWorkflowStorageService

    get_settings.cache_clear()
    llm = StubLLM(['["沈砚"]', "沈砚压低声音，指节扣住账册边缘。"])
    pipeline = NovelWorkflowPipeline(
        llm_complete=llm,
        storage_service=NovelWorkflowStorageService(),
        checkpointer=InMemorySaver(),
    )

    result = await pipeline.run(
        run_id="run-selection-rewrite-focused-context",
        initial_state={
            "intent_type": "selection_rewrite",
            "project_description": "寒门少年入局。",
            "current_chapter_context": "沈砚正在逼问账房。",
            "text_before_selection": "烛火摇了一下。",
            "selected_text": "沈砚按住账册。",
            "text_after_selection": "账房的脸色白了。",
            "rewrite_instruction": "加强压迫感，保留动作含义。",
            "current_bible": {
                "world_building": "世界规则",
                "characters_blueprint": (
                    "## 沈砚\n- 角色功能：破局者\n\n"
                    "## 无关角色\n- 秘密正文：IRRELEVANT_BLUEPRINT"
                ),
                "characters_status": (
                    "## 沈砚\n- 当前状态：掌握账册\n\n"
                    "## 无关角色\n- 秘密正文：IRRELEVANT_STATUS"
                ),
                "outline_master": "总纲",
                "outline_detail": "本章逼问账房。",
                "runtime_state": "沈砚拿到账册。",
                "runtime_threads": "账册伏笔。",
                "story_summary": "沈砚已入局。",
            },
        },
    )

    assert result.persist_payload["markdown"] == "沈砚压低声音，指节扣住账册边缘。"
    assert [call["mode"] for call in llm.calls] == ["analysis", "immersion"]
    prose_call = llm.calls[1]
    assert "# Active Character Focus" in prose_call["system_prompt"]
    assert "角色功能：破局者" in prose_call["system_prompt"]
    assert "IRRELEVANT_BLUEPRINT" not in prose_call["system_prompt"]
    assert "IRRELEVANT_STATUS" not in prose_call["system_prompt"]
    assert "# Active Character Focus" in prose_call["user_context"]
    assert "## 选中文本" in prose_call["user_context"]
    assert "沈砚按住账册。" in prose_call["user_context"]
    assert "加强压迫感，保留动作含义。" in prose_call["user_context"]
    assert "只输出改写后的选中文本" in prose_call["user_context"]


@pytest.mark.asyncio
async def test_chapter_write_beat_expansion_reuses_one_focused_context(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    from app.core.config import get_settings
    from app.services.novel_workflow_pipeline import NovelWorkflowPipeline
    from app.services.novel_workflow_storage import NovelWorkflowStorageService

    get_settings.cache_clear()
    llm = StubLLM(
        [
            '["沈砚"]',
            "第一拍正文",
            "## Verdict\npass\n## Conflicts\n无\n## Character Drift\n无\n## World Rule Issues\n无\n## Required Rewrites\n无",
            "第二拍正文",
            "## Verdict\npass\n## Conflicts\n无\n## Character Drift\n无\n## World Rule Issues\n无\n## Required Rewrites\n无",
        ]
    )
    pipeline = NovelWorkflowPipeline(
        llm_complete=llm,
        storage_service=NovelWorkflowStorageService(),
        checkpointer=InMemorySaver(),
    )

    prose, warnings = await pipeline._write_chapter_from_beats(
        {
            "run_id": "run-chapter-focused-context",
            "intent_type": "chapter_write",
            "beats_markdown": "- 第一拍\n- 第二拍",
            "current_chapter_context": "沈砚正在逼问账房。",
            "text_before_cursor": "沈砚按住账册。",
            "current_bible": {
                "characters_blueprint": (
                    "## 沈砚\n- 角色功能：破局者\n\n"
                    "## 无关角色\n- 秘密正文：IRRELEVANT_BLUEPRINT"
                ),
                "characters_status": (
                    "## 沈砚\n- 当前状态：掌握账册\n\n"
                    "## 无关角色\n- 秘密正文：IRRELEVANT_STATUS"
                ),
                "outline_detail": "本章逼问账房。",
                "runtime_state": "沈砚拿到账册。",
                "runtime_threads": "账册伏笔。",
            },
        }
    )

    assert prose == "第一拍正文第二拍正文"
    assert warnings == []
    assert [call["mode"] for call in llm.calls] == [
        "analysis",
        "immersion",
        "analysis",
        "immersion",
        "analysis",
    ]
    expansion_calls = [call for call in llm.calls if call["mode"] == "immersion"]
    assert len(expansion_calls) == 2
    assert all("角色功能：破局者" in call["user_context"] for call in expansion_calls)
    assert all("IRRELEVANT_BLUEPRINT" not in call["user_context"] for call in expansion_calls)


@pytest.mark.asyncio
async def test_chapter_write_pipeline_pauses_on_beats_then_expands_with_one_focused_context(
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
            "- 第一拍\n- 第二拍",
            '["沈砚"]',
            "第一拍正文",
            "## Verdict\npass\n## Conflicts\n无\n## Character Drift\n无\n## World Rule Issues\n无\n## Required Rewrites\n无",
            "第二拍正文",
            "## Verdict\npass\n## Conflicts\n无\n## Character Drift\n无\n## World Rule Issues\n无\n## Required Rewrites\n无",
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
        "chapter_id": "chapter-1",
        "current_chapter_context": "沈砚正在逼问账房。",
        "text_before_cursor": "沈砚按住账册。",
        "current_bible": {
            "characters_blueprint": (
                "## 沈砚\n- 角色功能：破局者\n\n"
                "## 无关角色\n- 秘密正文：IRRELEVANT_BLUEPRINT"
            ),
            "characters_status": "## 沈砚\n- 当前状态：掌握账册",
            "outline_detail": "本章逼问账房。",
            "runtime_state": "沈砚拿到账册。",
            "runtime_threads": "账册伏笔。",
        },
    }

    with pytest.raises(NovelWorkflowAwaitingHuman) as exc_info:
        await pipeline.run(run_id="run-chapter-write", initial_state=initial_state)

    assert exc_info.value.checkpoint_kind == "beats"
    beats = await storage.read_stage_markdown_artifact("run-chapter-write", name="beats_markdown")
    assert beats == "- 第一拍\n- 第二拍"

    decisions["run-chapter-write"] = {
        "action": "approve",
        "artifact_name": "beats_markdown",
    }
    result = await pipeline.run(run_id="run-chapter-write", initial_state=initial_state)

    assert result.persist_payload["chapter"]["content"] == "第一拍正文第二拍正文"
    assert result.persist_payload["chapter"]["beats_markdown"] == "- 第一拍\n- 第二拍"
    assert result.latest_artifacts == ["beats_markdown", "prose_markdown"]
    assert [call["mode"] for call in llm.calls] == [
        "analysis",
        "analysis",
        "immersion",
        "analysis",
        "immersion",
        "analysis",
    ]
