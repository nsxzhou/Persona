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
        **_kwargs,
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


class FailingReviewLLM(StubLLM):
    async def __call__(
        self,
        *,
        system_prompt: str,
        user_context: str,
        mode: str,
        **kwargs,
    ) -> str:
        if mode == "analysis" and "连载章节质量审校人" in system_prompt:
            raise RuntimeError("review provider unavailable")
        return await super().__call__(
            system_prompt=system_prompt,
            user_context=user_context,
            mode=mode,
            **kwargs,
        )


class StubLLMWithKwargs(StubLLM):
    async def __call__(
        self,
        *,
        system_prompt: str,
        user_context: str,
        mode: str,
        **kwargs,
    ) -> str:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_context": user_context,
                "mode": mode,
                **kwargs,
            }
        )
        if not self._outputs:
            raise AssertionError("stub llm exhausted")
        return self._outputs.pop(0)


@pytest.mark.asyncio
async def test_section_generation_passes_project_name_to_prompt_context(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    from app.core.config import get_settings
    from app.services.novel_workflow_pipeline import NovelWorkflowPipeline
    from app.services.novel_workflow_storage import NovelWorkflowStorageService

    get_settings.cache_clear()
    llm = StubLLM(["# 《我在江湖开酒楼》 全书总纲\n\n## 第一阶段：开张"])
    pipeline = NovelWorkflowPipeline(
        llm_complete=llm,
        storage_service=NovelWorkflowStorageService(),
        checkpointer=InMemorySaver(),
    )

    result = await pipeline.run(
        run_id="run-section-project-name-context",
        initial_state={
            "intent_type": "section_generate",
            "section": "outline_master",
            "project_name": "请客官上座",
            "project_description": "掌柜在江湖酒楼接待各路客人。",
            "current_bible": {
                "world_building": "",
                "characters_blueprint": "",
                "outline_master": "",
                "outline_detail": "",
                "characters_status": "",
                "runtime_state": "",
                "runtime_threads": "",
            },
        },
    )

    assert result.persist_payload["markdown"] == "# 《请客官上座》 全书总纲\n\n## 第一阶段：开张"
    user_context = llm.calls[0]["user_context"]
    assert "## 项目小说名（硬约束）\n\n请客官上座" in user_context
    assert "必须逐字使用上面的项目小说名" in user_context
    assert "## 简介\n\n掌柜在江湖酒楼接待各路客人。" in user_context


@pytest.mark.asyncio
async def test_outline_master_generation_adds_project_title_when_missing(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    from app.core.config import get_settings
    from app.services.novel_workflow_pipeline import NovelWorkflowPipeline
    from app.services.novel_workflow_storage import NovelWorkflowStorageService

    get_settings.cache_clear()
    llm = StubLLM(["## 第一阶段：开张"])
    pipeline = NovelWorkflowPipeline(
        llm_complete=llm,
        storage_service=NovelWorkflowStorageService(),
        checkpointer=InMemorySaver(),
    )

    result = await pipeline.run(
        run_id="run-section-project-name-title-missing",
        initial_state={
            "intent_type": "section_generate",
            "section": "outline_master",
            "project_name": "请客官上座",
            "current_bible": {},
        },
    )

    assert result.persist_payload["markdown"] == "# 《请客官上座》 全书总纲\n\n## 第一阶段：开张"


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
async def test_imported_chapter_full_rewrite_prompt_uses_adjacent_window_and_excludes_planning_context(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    from app.core.config import get_settings
    from app.services.novel_workflow_pipeline import NovelWorkflowPipeline
    from app.services.novel_workflow_storage import NovelWorkflowStorageService

    get_settings.cache_clear()
    original = "沈砚推开窗，雨落进来。他合上卷宗，停在门前。"
    rewritten = "沈砚推开窗，冷雨压低了呼吸。他合上卷宗，停在门前。"
    plan_yaml = f"""---
edits:
  - operation: replace
    paragraph_id: P001
    new_text: |-
      {rewritten}
---
"""
    llm = StubLLMWithKwargs(['["沈砚"]', plan_yaml])
    storage = NovelWorkflowStorageService()
    pipeline = NovelWorkflowPipeline(
        llm_complete=llm,
        storage_service=storage,
        checkpointer=InMemorySaver(),
    )

    result = await pipeline.run(
        run_id="run-imported-rewrite-context",
        initial_state={
            "intent_type": "imported_chapter_full_rewrite",
            "project_description": "SHOULD_NOT_APPEAR_PROJECT_CONTEXT",
            "style_prompt": "短句、冷雨、低声对白。",
            "plot_prompt": "SHOULD_NOT_APPEAR_PLOT_GUIDE",
            "current_chapter_context": "第2章 旧卷宗",
            "selected_text": original,
            "rewrite_instruction": "增强压迫感，不要改变结尾。",
            "expansion_ratio_percent": 14,
            "imported_previous_chapter": {
                "title": "第1章 雨夜归来",
                "summary": "沈砚回城。",
                "excerpt": "上一章尾声：城门在雨里合上。",
            },
            "imported_next_chapter": {
                "title": "第3章 暗巷灯火",
                "summary": "暗巷出现新线索。",
                "excerpt": "下一章开头：灯火在暗巷尽头亮起。",
            },
            "chapter_snapshot": {
                "title": "第2章 旧卷宗",
                "content": original,
                "summary": "",
            },
            "current_bible": {
                "world_building": "SHOULD_NOT_APPEAR_WORLD",
                "characters_blueprint": (
                    "## 沈砚\n- 查案者\n\n"
                    "## 无关角色\n- SHOULD_NOT_APPEAR_CHARACTER"
                ),
                "characters_status": "## 沈砚\n- 刚拿到卷宗",
                "outline_master": "SHOULD_NOT_APPEAR_MASTER",
                "outline_detail": "SHOULD_NOT_APPEAR_OUTLINE_NAV",
                "runtime_state": "SHOULD_NOT_APPEAR_RUNTIME_STATE",
                "runtime_threads": "SHOULD_NOT_APPEAR_RUNTIME_THREADS",
                "story_summary": "SHOULD_NOT_APPEAR_STORY_SUMMARY",
            },
        },
    )

    assert result.persist_payload["markdown"] == rewritten
    assert result.persist_payload["plan_yaml"] == plan_yaml.strip()
    assert [call["mode"] for call in llm.calls] == ["analysis", "immersion"]
    active_call = llm.calls[0]
    assert "沈砚推开窗" in active_call["user_context"]
    assert "他合上卷宗" in active_call["user_context"]
    prose_call = llm.calls[1]
    assert "## 目标章节标题（仅定位参考，不要输出）" in prose_call["user_context"]
    assert "第2章 旧卷宗" in prose_call["user_context"]
    assert "## 上一章边界参考" in prose_call["user_context"]
    assert "上一章尾声" in prose_call["user_context"]
    assert "## 编号后的当前章节原文（唯一改写目标）" in prose_call["user_context"]
    assert "[P001]\n沈砚推开窗，雨落进来" in prose_call["user_context"]
    assert "## 下一章边界参考（不得写入输出）" in prose_call["user_context"]
    assert "下一章开头" in prose_call["user_context"]
    assert "增强压迫感" in prose_call["user_context"]
    assert "不要输出章节标题" in prose_call["user_context"]
    assert "只输出 YAML front matter 改写计划" in prose_call["system_prompt"]
    assert "不得输出改写后的完整章节" in prose_call["system_prompt"]
    assert "`operation` 只能是 `insert_after` 或 `replace`" in prose_call["system_prompt"]
    assert "Plot Writing Guide disabled" in prose_call["system_prompt"]
    assert "短句、冷雨、低声对白。" in prose_call["system_prompt"]
    assert "查案者" in prose_call["system_prompt"]
    for forbidden in (
        "SHOULD_NOT_APPEAR_PROJECT_CONTEXT",
        "SHOULD_NOT_APPEAR_PLOT_GUIDE",
        "SHOULD_NOT_APPEAR_WORLD",
        "SHOULD_NOT_APPEAR_MASTER",
        "SHOULD_NOT_APPEAR_OUTLINE_NAV",
        "SHOULD_NOT_APPEAR_RUNTIME_STATE",
        "SHOULD_NOT_APPEAR_RUNTIME_THREADS",
        "SHOULD_NOT_APPEAR_STORY_SUMMARY",
        "SHOULD_NOT_APPEAR_CHARACTER",
    ):
        assert forbidden not in prose_call["system_prompt"]
        assert forbidden not in prose_call["user_context"]
    manifest = prose_call["prompt_stack_manifest"]["imported_rewrite_context"]
    assert manifest["intent"] == "imported_chapter_full_rewrite"
    assert manifest["context_policy"] == "imported_chapter_adjacent_window_v1"
    assert manifest["target_chapter_title"] == "第2章 旧卷宗"
    assert manifest["previous_context_title"] == "第1章 雨夜归来"
    assert manifest["previous_context_char_count"] == len(
        "第1章 雨夜归来" + "沈砚回城。" + "上一章尾声：城门在雨里合上。"
    )
    assert manifest["next_context_title"] == "第3章 暗巷灯火"
    assert manifest["next_context_char_count"] == len(
        "第3章 暗巷灯火" + "暗巷出现新线索。" + "下一章开头：灯火在暗巷尽头亮起。"
    )
    assert manifest["voice_profile_injected"] is True
    assert manifest["plot_guide_disabled"] is True
    assert manifest["active_character_names"] == ["沈砚"]

    stored = await storage.read_stage_markdown_artifact(
        "run-imported-rewrite-context",
        name="chapter_rewrite_markdown",
    )
    assert stored == rewritten
    raw_plan = await storage.read_stage_markdown_artifact(
        "run-imported-rewrite-context",
        name="chapter_rewrite_plan_yaml",
    )
    assert raw_plan == plan_yaml.strip()


@pytest.mark.asyncio
async def test_imported_chapter_full_rewrite_retries_invalid_patch_and_stores_successful_output(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    from app.core.config import get_settings
    from app.services.novel_workflow_pipeline import NovelWorkflowPipeline
    from app.services.novel_workflow_storage import NovelWorkflowStorageService

    get_settings.cache_clear()
    original = "第一段落写完了。\n\n第二段落收束。"
    invalid_plan = """---
edits:
  - operation: replace
    paragraph_id: P999
    new_text: |-
      第一段落写完了，雨声压住了窗棂。
---"""
    valid_plan = """---
edits:
  - operation: insert_after
    paragraph_id: P001
    new_text: |-
      雨声压住了窗棂，屋内的人都放轻了呼吸。
---
"""
    llm = StubLLM(['["沈砚"]', invalid_plan, '["沈砚"]', valid_plan])
    storage = NovelWorkflowStorageService()
    pipeline = NovelWorkflowPipeline(
        llm_complete=llm,
        storage_service=storage,
        checkpointer=InMemorySaver(),
    )

    result = await pipeline.run(
        run_id="run-imported-rewrite-patch-retry",
        initial_state={
            "intent_type": "imported_chapter_full_rewrite",
            "rewrite_instruction": "增加雨夜压迫感",
            "chapter_snapshot": {"title": "第2章", "content": original},
            "current_bible": {},
        },
    )

    synthesized = "第一段落写完了。\n\n雨声压住了窗棂，屋内的人都放轻了呼吸。\n\n第二段落收束。"
    assert result.persist_payload["markdown"] == synthesized
    assert result.persist_payload["plan_yaml"] == valid_plan.strip()
    retry_prompt = llm.calls[3]["user_context"]
    assert invalid_plan.strip() in retry_prompt
    assert "章节改写计划 paragraph_id 不存在" in retry_prompt
    assert "YAML front matter" in retry_prompt
    assert (
        await storage.read_stage_markdown_artifact(
            "run-imported-rewrite-patch-retry",
            name="chapter_rewrite_plan_yaml",
        )
        == valid_plan.strip()
    )


@pytest.mark.asyncio
async def test_imported_chapter_full_rewrite_omits_active_character_block_when_no_match(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    from app.core.config import get_settings
    from app.services.novel_workflow_pipeline import NovelWorkflowPipeline
    from app.services.novel_workflow_storage import NovelWorkflowStorageService

    get_settings.cache_clear()
    llm = StubLLMWithKwargs(
        [
            "[]",
            """---
edits:
  - operation: replace
    paragraph_id: P001
    new_text: |-
      原正文仍停在门前。
---""",
        ]
    )
    pipeline = NovelWorkflowPipeline(
        llm_complete=llm,
        storage_service=NovelWorkflowStorageService(),
        checkpointer=InMemorySaver(),
    )

    await pipeline.run(
        run_id="run-imported-rewrite-no-character",
        initial_state={
            "intent_type": "imported_chapter_full_rewrite",
            "selected_text": "原正文停在门前。",
            "chapter_snapshot": {"title": "第2章", "content": "原正文停在门前。"},
            "expansion_ratio_percent": 12,
            "current_bible": {
                "characters_blueprint": "## 沈砚\n- 查案者",
                "characters_status": "## 沈砚\n- 当前状态",
            },
        },
    )

    prose_call = llm.calls[1]
    assert "Active Character Reference" not in prose_call["system_prompt"]
    assert "未识别到明确活跃角色" not in prose_call["system_prompt"]
    assert prose_call["prompt_stack_manifest"]["imported_rewrite_context"][
        "active_character_names"
    ] == []
    assert prose_call["prompt_stack_manifest"]["imported_rewrite_context"][
        "active_character_material_char_count"
    ] == 0


@pytest.mark.asyncio
async def test_chapter_enrichment_rewrite_stores_synthesized_and_raw_patch_artifacts(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    from app.core.config import get_settings
    from app.services.novel_workflow_pipeline import NovelWorkflowPipeline
    from app.services.novel_workflow_storage import NovelWorkflowStorageService

    get_settings.cache_clear()
    original = "第一段落写完了。\n\n第二段落收束。"
    raw_plan = """---
edits:
  - operation: insert_after
    paragraph_id: P001
    new_text: |-
      新增气氛，灯影在墙上慢慢压下来。
---
"""
    llm = StubLLM(['["沈砚"]', raw_plan])
    storage = NovelWorkflowStorageService()
    pipeline = NovelWorkflowPipeline(
        llm_complete=llm,
        storage_service=storage,
        checkpointer=InMemorySaver(),
    )

    result = await pipeline.run(
        run_id="run-chapter-enrichment-patches",
        initial_state={
            "intent_type": "chapter_enrichment_rewrite",
            "selected_text": original,
            "text_before_cursor": original,
            "rewrite_instruction": "增加气氛",
            "expansion_ratio_percent": 40,
            "chapter_snapshot": {
                "title": "第1章",
                "content": original,
            },
            "current_bible": {},
        },
    )

    synthesized = "第一段落写完了。\n\n新增气氛，灯影在墙上慢慢压下来。\n\n第二段落收束。"
    assert result.persist_payload["markdown"] == synthesized
    assert result.persist_payload["plan_yaml"] == raw_plan.strip()
    assert result.latest_artifacts == [
        "chapter_rewrite_markdown",
        "chapter_rewrite_plan_yaml",
    ]
    assert (
        await storage.read_stage_markdown_artifact(
            "run-chapter-enrichment-patches",
            name="chapter_rewrite_markdown",
        )
        == synthesized
    )
    assert (
        await storage.read_stage_markdown_artifact(
            "run-chapter-enrichment-patches",
            name="chapter_rewrite_plan_yaml",
        )
        == raw_plan.strip()
    )


@pytest.mark.asyncio
async def test_chapter_enrichment_rewrite_retries_invalid_patch_and_stores_successful_output(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    from app.core.config import get_settings
    from app.services.novel_workflow_pipeline import NovelWorkflowPipeline
    from app.services.novel_workflow_storage import NovelWorkflowStorageService

    get_settings.cache_clear()
    original = "第一段落写完了。\n\n第二段落收束。"
    invalid_plan = """---
edits:
  - operation: replace
    paragraph_id: P999
    new_text: |-
      第一段落写完了，灯影晃了一下。
---"""
    valid_plan = """---
edits:
  - operation: insert_after
    paragraph_id: P001
    new_text: |-
      灯影晃了一下，把沉默拉得更长。
---
"""
    llm = StubLLM(['["沈砚"]', invalid_plan, '["沈砚"]', valid_plan])
    storage = NovelWorkflowStorageService()
    pipeline = NovelWorkflowPipeline(
        llm_complete=llm,
        storage_service=storage,
        checkpointer=InMemorySaver(),
    )

    result = await pipeline.run(
        run_id="run-chapter-enrichment-patch-retry",
        initial_state={
            "intent_type": "chapter_enrichment_rewrite",
            "selected_text": original,
            "rewrite_instruction": "增加压迫感",
            "chapter_snapshot": {"title": "第1章", "content": original},
            "current_bible": {},
        },
    )

    synthesized = "第一段落写完了。\n\n灯影晃了一下，把沉默拉得更长。\n\n第二段落收束。"
    assert result.persist_payload["markdown"] == synthesized
    assert result.persist_payload["plan_yaml"] == valid_plan.strip()
    retry_prompt = llm.calls[3]["user_context"]
    assert invalid_plan.strip() in retry_prompt
    assert "章节改写计划 paragraph_id 不存在" in retry_prompt
    assert "YAML front matter" in retry_prompt
    assert (
        await storage.read_stage_markdown_artifact(
            "run-chapter-enrichment-patch-retry",
            name="chapter_rewrite_plan_yaml",
        )
        == valid_plan.strip()
    )


@pytest.mark.asyncio
async def test_chapter_enrichment_rewrite_retries_under_budget_plan_as_expand_on_existing(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    from app.core.config import get_settings
    from app.services.novel_workflow_pipeline import NovelWorkflowPipeline
    from app.services.novel_workflow_storage import NovelWorkflowStorageService

    get_settings.cache_clear()
    original = "1234567890\n\n第二段。"
    under_budget_plan = """---
edits:
  - operation: insert_after
    paragraph_id: P001
    new_text: |-
      短。
---"""
    valid_plan = """---
edits:
  - operation: insert_after
    paragraph_id: P001
    new_text: |-
      补足后的气氛段落，加入更多动作、环境与心理变化，让增长达到预算。
---"""
    llm = StubLLM(['[]', under_budget_plan, '[]', valid_plan])
    storage = NovelWorkflowStorageService()
    pipeline = NovelWorkflowPipeline(
        llm_complete=llm,
        storage_service=storage,
        checkpointer=InMemorySaver(),
    )

    result = await pipeline.run(
        run_id="run-chapter-enrichment-under-budget-retry",
        initial_state={
            "intent_type": "chapter_enrichment_rewrite",
            "selected_text": original,
            "rewrite_instruction": "扩写气氛",
            "expansion_ratio_percent": 100,
            "chapter_snapshot": {"title": "第1章", "content": original},
            "current_bible": {},
        },
    )

    assert result.persist_payload["plan_yaml"] == valid_plan.strip()
    assert "补足后的气氛段落" in result.persist_payload["markdown"]
    retry_prompt = llm.calls[3]["user_context"]
    assert under_budget_plan.strip() in retry_prompt
    assert "结构有效，但扩写字数不足" in retry_prompt
    assert "不要丢弃上一版有效计划" in retry_prompt
    assert "优先扩写上一版 edits 的 new_text" in retry_prompt


@pytest.mark.asyncio
async def test_chapter_rewrite_no_patches_fails_workflow(
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
            '[]',
            "---\nedits: []\n---",
            '[]',
            "---\nedits: []\n---",
            '[]',
            "---\nedits: []\n---",
        ]
    )
    pipeline = NovelWorkflowPipeline(
        llm_complete=llm,
        storage_service=NovelWorkflowStorageService(),
        checkpointer=InMemorySaver(),
    )

    with pytest.raises(ValueError, match="edits 必须是非空列表"):
        await pipeline.run(
            run_id="run-chapter-rewrite-no-patches",
            initial_state={
                "intent_type": "chapter_enrichment_rewrite",
                "selected_text": "第一段。",
                "chapter_snapshot": {"title": "第1章", "content": "第一段。"},
                "current_bible": {},
            },
        )


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


def test_imported_chapter_rewrite_validation_fatal_cases() -> None:
    from app.prompts.imported_chapter_rewrite import (
        validate_imported_chapter_rewrite_output,
    )

    original = "原章节正文。" * 20
    next_chapter = {
        "title": "第3章 暗巷灯火",
        "excerpt": "下一章开头出现新线索，灯火在暗巷尽头亮起，沈砚听见陌生人的脚步声。",
    }

    fatal_cases = [
        "",
        "以下是改写后的正文：\n原章节正文。",
        "- 改写要点\n- 第一\n- 第二",
        "第3章 暗巷灯火\n下一章开头出现新线索，灯火在暗巷尽头亮起。",
        "太短",
    ]
    for output in fatal_cases:
        with pytest.raises(ValueError):
            validate_imported_chapter_rewrite_output(
                output=output,
                original=original,
                target_title="第2章 旧卷宗",
                next_chapter=next_chapter,
                user_instruction="润色",
            )


def test_imported_chapter_rewrite_validation_warning_cases() -> None:
    from app.prompts.imported_chapter_rewrite import (
        validate_imported_chapter_rewrite_output,
    )

    original = "“去查。”沈砚推门。她点头。“现在？”“现在。”他停在门前。" * 6
    output = "第2章 旧卷宗\n" + ("沈砚沉默地停在门前。" * 36)

    warnings = validate_imported_chapter_rewrite_output(
        output=output,
        original=original,
        target_title="第2章 旧卷宗",
        next_chapter=None,
        user_instruction="补写省略处并丰富细节",
    )

    assert "imported_rewrite_length_180_300_percent" in warnings
    assert "imported_rewrite_possible_chapter_title" in warnings
    assert "imported_rewrite_possible_dialogue_or_action_loss" in warnings
    assert "imported_rewrite_substantial_localized_expansion" in warnings


def test_parse_prompt_asset_init_response_accepts_fenced_json() -> None:
    from app.prompts.prompt_asset_init import parse_prompt_asset_init_response

    parsed = parse_prompt_asset_init_response(
        r"""```json
{
  "changes": [
    {
      "action": "new",
      "rationale": "主角资产缺失",
      "payload": {
        "kind": "character_card",
        "scope": "project",
        "chapter_id": null,
        "title": "沈砚",
        "content": "## 沈砚\n- 破局者",
        "keywords": ["沈砚"],
        "enabled": true,
        "always_on": false,
        "priority": 20
      }
    }
  ]
}
```"""
    )

    assert parsed.changes[0].action == "new"
    assert parsed.changes[0].payload is not None
    assert parsed.changes[0].payload.kind == "character_card"
    assert parsed.changes[0].payload.keywords == ["沈砚"]


@pytest.mark.asyncio
async def test_prompt_asset_init_generates_suggestion_artifact_without_writeback(
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
            '{"changes":[{"action":"new","rationale":"补齐世界书","payload":{"kind":"lorebook_entry","scope":"project","chapter_id":null,"title":"雨城","content":"雨城常年阴雨。","keywords":["雨城"],"enabled":true,"always_on":false,"priority":10}}]}'
        ]
    )
    storage = NovelWorkflowStorageService()
    pipeline = NovelWorkflowPipeline(
        llm_complete=llm,
        storage_service=storage,
        checkpointer=InMemorySaver(),
    )

    result = await pipeline.run(
        run_id="run-prompt-asset-init",
        initial_state={
            "intent_type": "prompt_asset_init",
            "project_name": "雨城旧账",
            "project_description": "在雨城追查旧案。",
            "current_bible": {
                "world_building": "雨城常年阴雨。",
                "characters_blueprint": "## 沈砚\n- 查案者",
            },
            "prompt_assets": [],
        },
    )

    assert result.latest_artifacts == ["prompt_asset_suggestions"]
    assert "project_bible" not in result.persist_payload
    artifact = await storage.read_stage_markdown_artifact(
        "run-prompt-asset-init",
        name="prompt_asset_suggestions",
    )
    assert '"action": "new"' in artifact
    assert '"title": "雨城"' in artifact
    assert "雨城常年阴雨" in llm.calls[0]["user_context"]
    assert "existing_prompt_assets" in llm.calls[0]["user_context"]


@pytest.mark.asyncio
async def test_chapter_write_retries_when_limited_third_output_uses_first_person_narration(
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
            "- 第一拍",
            '["沈砚"]',
            "我推开门，冷风灌进来。",
            "## Verdict\npass\n## Conflicts\n无\n## Character Drift\n无\n## World Rule Issues\n无\n## Required Rewrites\n无",
            '["沈砚"]',
            "沈砚推开门，冷风灌进来。",
            "## Verdict\npass\n## Conflicts\n无\n## Character Drift\n无\n## World Rule Issues\n无\n## Required Rewrites\n无",
        ]
    )
    storage = NovelWorkflowStorageService()
    pipeline = NovelWorkflowPipeline(
        llm_complete=llm,
        storage_service=storage,
        checkpointer=InMemorySaver(),
        decision_loader=lambda _run_id: {
            "action": "approve",
            "artifact_name": "beats_markdown",
        },
    )

    result = await pipeline.run(
        run_id="run-chapter-write-limited-third-retry",
        initial_state={
            "intent_type": "chapter_write",
            "chapter_id": "chapter-1",
            "current_chapter_context": "沈砚进入账房。",
            "text_before_cursor": "",
            "current_bible": {
                "characters_blueprint": "## 沈砚\n- 角色功能：破局者",
                "characters_status": "## 沈砚\n- 当前状态：掌握账册",
                "outline_detail": "本章进入账房。",
                "runtime_state": "沈砚准备逼问账房。",
                "runtime_threads": "账册伏笔。",
            },
        },
    )

    assert result.persist_payload["chapter"]["content"] == "沈砚推开门，冷风灌进来。"
    assert "我推开门" not in result.persist_payload["chapter"]["content"]
    assert "limited_third_pov_retry" in result.warnings


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


@pytest.mark.asyncio
async def test_beat_expand_injects_prompt_asset_layers_in_runtime_order(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    from app.core.config import get_settings
    from app.services.context_assembly import WritingPromptAssetLayer
    from app.services.novel_workflow_pipeline import NovelWorkflowPipeline
    from app.services.novel_workflow_storage import NovelWorkflowStorageService
    from app.schemas.projects import PromptStackManifest
    from app.services.prompt_stack import PromptStackSelection

    get_settings.cache_clear()
    llm = StubLLM(
        [
            "[]",
            "Expanded prose",
            "Expanded prose",
            "Expanded prose",
            "Expanded prose",
            "Expanded prose",
        ]
    )
    pipeline = NovelWorkflowPipeline(
        llm_complete=llm,
        storage_service=NovelWorkflowStorageService(),
        checkpointer=InMemorySaver(),
    )
    prompt_stack = PromptStackSelection(
        layers=[
            WritingPromptAssetLayer(
                key="author_notes",
                title="Author Notes",
                content="# Author Notes\n\nNear output note",
            ),
            WritingPromptAssetLayer(
                key="active_character_cards",
                title="Active Character Cards",
                content="# Active Character Cards\n\nCharacter runtime card",
            ),
            WritingPromptAssetLayer(
                key="active_lorebook_entries",
                title="Active Lorebook Entries",
                content="# Active Lorebook Entries\n\nLore runtime entry",
            ),
        ],
        selected_assets=[],
        manifest=PromptStackManifest(
            layers=[],
            selected_assets=[],
            total_selected_assets=0,
            final_prompt_char_count=0,
        ),
    )

    result = await pipeline._handle_beat_expand(
        {
            "run_id": "run-beat-expand-prompt-stack",
            "intent_type": "beat_expand",
            "beat": "Open the river gate",
            "beat_index": 0,
            "total_beats": 1,
            "current_chapter_context": "river gate scene",
            "current_bible": {},
            "prompt_stack": prompt_stack,
        },
        {},
        pipeline._generation_profile_obj({}),
    )

    assert result["persist_payload"]["markdown"] == "Expanded prose"
    user_context = next(call["user_context"] for call in llm.calls if call["mode"] == "immersion")
    assert user_context.index("# Active Lorebook Entries") < user_context.index("# Active Character Cards")
    assert user_context.index("# Active Character Cards") < user_context.index("# Author Notes")
    assert user_context.index("# Author Notes") < user_context.index("## 完整节拍列表（必须按顺序覆盖）")


@pytest.mark.asyncio
async def test_chapter_expand_generates_serial_beat_calls_with_prior_prose_context(
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
            "[]",
            "第一拍正文",
            "第二拍正文",
            "第三拍正文",
            '{"issues":["漏掉第 3 拍","章末钩子偏弱"]}',
        ]
    )
    storage = NovelWorkflowStorageService()
    pipeline = NovelWorkflowPipeline(
        llm_complete=llm,
        storage_service=storage,
        checkpointer=InMemorySaver(),
    )

    result = await pipeline.run(
        run_id="run-chapter-expand",
        initial_state={
            "intent_type": "chapter_expand",
            "beats": ["第一拍", "第二拍", "第三拍"],
            "current_chapter_context": "本章上下文",
            "current_bible": {
                "outline_detail": "章节细纲",
                "runtime_state": "运行状态",
                "runtime_threads": "伏笔",
            },
        },
    )

    assert result.persist_payload["markdown"] == "第一拍正文\n\n第二拍正文\n\n第三拍正文"
    assert result.persist_payload["review_issues"] == ["漏掉第 3 拍", "章末钩子偏弱"]
    assert result.warnings == ["漏掉第 3 拍", "章末钩子偏弱"]
    assert result.latest_artifacts == ["prose_markdown", "chapter_expand_review"]
    assert (
        await storage.read_stage_markdown_artifact(
            "run-chapter-expand",
            name="prose_markdown",
        )
        == "第一拍正文\n\n第二拍正文\n\n第三拍正文"
    )
    assert await storage.read_stage_markdown_artifact("run-chapter-expand", name="chapter_expand_review") == '{"issues":["漏掉第 3 拍","章末钩子偏弱"]}'
    immersion_calls = [call for call in llm.calls if call["mode"] == "immersion"]
    assert len(immersion_calls) == 3
    assert "3000-5000 个中文字符" in immersion_calls[0]["system_prompt"]
    assert "第 1/3 拍：第一拍" in immersion_calls[0]["user_context"]
    assert "第 2/3 拍：第二拍" in immersion_calls[1]["user_context"]
    assert "已生成正文衔接参考：第一拍正文" in immersion_calls[1]["user_context"]
    assert "第 3/3 拍：第三拍" in immersion_calls[2]["user_context"]
    assert "已生成正文衔接参考：第一拍正文\n\n第二拍正文" in immersion_calls[2]["user_context"]


@pytest.mark.asyncio
async def test_chapter_expand_clean_review_has_no_warnings(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    from app.core.config import get_settings
    from app.services.novel_workflow_pipeline import NovelWorkflowPipeline
    from app.services.novel_workflow_storage import NovelWorkflowStorageService

    get_settings.cache_clear()
    llm = StubLLM(["[]", "第一拍正文", "第二拍正文", '{"issues":[]}'])
    pipeline = NovelWorkflowPipeline(
        llm_complete=llm,
        storage_service=NovelWorkflowStorageService(),
        checkpointer=InMemorySaver(),
    )

    result = await pipeline.run(
        run_id="run-chapter-expand-clean-review",
        initial_state={
            "intent_type": "chapter_expand",
            "beats": ["第一拍", "第二拍"],
            "current_bible": {},
        },
    )

    assert result.persist_payload["markdown"] == "第一拍正文\n\n第二拍正文"
    assert result.persist_payload["review_issues"] == []
    assert result.warnings == []


@pytest.mark.asyncio
async def test_chapter_expand_review_failure_does_not_block_delivery(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", "test-encryption-key-123456789012")
    from app.core.config import get_settings
    from app.services.novel_workflow_pipeline import NovelWorkflowPipeline
    from app.services.novel_workflow_storage import NovelWorkflowStorageService

    get_settings.cache_clear()
    storage = NovelWorkflowStorageService()
    llm = FailingReviewLLM(["[]", "第一拍正文", "第二拍正文"])
    pipeline = NovelWorkflowPipeline(
        llm_complete=llm,
        storage_service=storage,
        checkpointer=InMemorySaver(),
    )

    result = await pipeline.run(
        run_id="run-chapter-expand-review-failure",
        initial_state={
            "intent_type": "chapter_expand",
            "beats": ["第一拍", "第二拍"],
            "current_bible": {},
        },
    )

    assert result.persist_payload["markdown"] == "第一拍正文\n\n第二拍正文"
    assert result.persist_payload["review_issues"] == [
        "章节审校未完成：审校调用失败，已保留生成正文"
    ]
    assert result.warnings == ["章节审校未完成：审校调用失败，已保留生成正文"]
    assert (
        await storage.read_stage_markdown_artifact(
            "run-chapter-expand-review-failure",
            name="prose_markdown",
        )
        == "第一拍正文\n\n第二拍正文"
    )
