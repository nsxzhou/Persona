from __future__ import annotations

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from app.services.beat_parser import parse_beats_markdown


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
async def test_volume_chapters_generation_uses_target_volume_context(
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
            "### 第 9 章：追捕升级\n"
            "- **核心事件**：庄晏建立信息网络。\n"
            "- **情绪走向**：紧张 → 冷静\n"
            "- **章末钩子**：林景行扑空。"
        ]
    )
    pipeline = NovelWorkflowPipeline(
        llm_complete=llm,
        storage_service=NovelWorkflowStorageService(),
        checkpointer=InMemorySaver(),
    )

    result = await pipeline.run(
        run_id="run-volume-chapters-context",
        initial_state={
            "intent_type": "volume_chapters_generate",
            "volume_index": 1,
            "current_bible": {
                "outline_master": "全书总纲",
                "outline_detail": (
                    "## 第一卷：撕掉标签\n"
                    "> 主题：先反制系统\n\n"
                    "### 第 1 章：诊断书\n"
                    "- **核心事件**：庄晏拿到诊断书\n\n"
                    "## 第二卷：偷来的自由\n"
                    "> 主题：在追捕中学会呼吸\n\n"
                    "### 核心驱动轴\n"
                    "建立灰色网络，从猎物变成猎人。\n"
                ),
            },
        },
    )

    assert result.persist_payload["markdown"].startswith("### 第 9 章")
    user_context = llm.calls[0]["user_context"]
    assert "**第二卷：偷来的自由**" in user_context
    assert "主题：在追捕中学会呼吸" in user_context
    assert "### 当前卷原始规划" in user_context
    assert "建立灰色网络，从猎物变成猎人。" in user_context
    assert "## 前几卷已有章节（参考，保持连贯）" in user_context
    assert "庄晏拿到诊断书" in user_context


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
    assert all("视角约束" in call["system_prompt"] for call in expansion_calls)
    assert all("不要写括号式内心独白" in call["system_prompt"] for call in expansion_calls)
    assert all("角色功能：破局者" in call["user_context"] for call in expansion_calls)
    assert all("IRRELEVANT_BLUEPRINT" not in call["user_context"] for call in expansion_calls)


def test_parse_beats_markdown_prefers_explicit_bracketed_beats_and_skips_noise() -> None:
    markdown = (
        "节拍如下：\n"
        "- [平静→疑惑] 主角注意到脚印\n"
        "- 【紧绷→爆发】 班主任刚开口\n"
        "3. [爆发→压制] 林景行看着他\n"
        "### 说明\n"
        "[震惊→决然] 他走了两步\n"
        "注：别输出标题"
    )

    assert parse_beats_markdown(markdown) == [
        "[平静→疑惑] 主角注意到脚印",
        "[紧绷→爆发] 班主任刚开口",
        "[爆发→压制] 林景行看着他",
        "[震惊→决然] 他走了两步",
    ]


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


def test_parse_beats_markdown_normalizes_list_markers_for_chapter_expansion() -> None:
    assert parse_beats_markdown("- 第一拍\n- 第二拍") == ["第一拍", "第二拍"]
