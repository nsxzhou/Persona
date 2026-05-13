from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.prompts.imported_chapter_rewrite import (
    build_imported_chapter_rewrite_system_prompt,
    build_imported_chapter_rewrite_user_context,
    build_imported_context_manifest,
    state_chapter_content,
    state_chapter_title,
    state_imported_chapter,
    validate_imported_chapter_rewrite_output,
)
from app.schemas.prompt_profiles import build_chapter_objective_card, build_intensity_profile
from app.services.chapter_rewrite_patches import (
    build_numbered_chapter_rewrite_source,
    synthesize_chapter_rewrite_plan,
)
from app.services.context_assembly import WritingContextSections, assemble_writing_context
from app.services.novel_workflow_handler_common import (
    NovelWorkflowPipelineContext,
    NovelWorkflowState,
    state_prompt_asset_layers,
    state_prompt_stack_manifest,
)


CHAPTER_REWRITE_ARTIFACT = "chapter_rewrite_markdown"
CHAPTER_REWRITE_PLAN_ARTIFACT = "chapter_rewrite_plan_yaml"
_CHAPTER_REWRITE_PATCH_MAX_ATTEMPTS = 3
_CHAPTER_REWRITE_RETRY_OUTPUT_CHARS = 8_000


class NovelWorkflowRewriteHandlers:
    def __init__(self, pipeline: NovelWorkflowPipelineContext) -> None:
        self.pipeline = pipeline

    async def handle_selection_rewrite(
        self,
        state: NovelWorkflowState,
        _current_bible: dict[str, str],
        _generation_profile: Any,
    ) -> dict[str, Any]:
        artifact_name = "prose_markdown"
        markdown = await self.generate_selection_rewrite(state)
        await self.pipeline.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name=artifact_name,
            markdown=markdown,
        )
        return {
            "latest_artifacts": [artifact_name],
            "persist_payload": {"markdown": markdown},
        }

    async def handle_chapter_enrichment_rewrite(
        self,
        state: NovelWorkflowState,
        _current_bible: dict[str, str],
        _generation_profile: Any,
    ) -> dict[str, Any]:
        original = self.chapter_enrichment_rewrite_source_text(state)
        plan_yaml, markdown = await self.generate_valid_chapter_rewrite_plan(
            state=state,
            original=original,
            generator=self.generate_chapter_enrichment_rewrite,
        )
        await self.pipeline.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name=CHAPTER_REWRITE_PLAN_ARTIFACT,
            markdown=plan_yaml,
        )
        await self.pipeline.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name=CHAPTER_REWRITE_ARTIFACT,
            markdown=markdown,
        )
        return {
            "latest_artifacts": [CHAPTER_REWRITE_ARTIFACT, CHAPTER_REWRITE_PLAN_ARTIFACT],
            "persist_payload": {
                "markdown": markdown,
                "plan_yaml": plan_yaml,
            },
        }

    async def handle_imported_chapter_full_rewrite(
        self,
        state: NovelWorkflowState,
        _current_bible: dict[str, str],
        _generation_profile: Any,
    ) -> dict[str, Any]:
        original = state_chapter_content(state)
        plan_yaml, markdown = await self.generate_valid_chapter_rewrite_plan(
            state=state,
            original=original,
            generator=self.generate_imported_chapter_full_rewrite,
        )
        validation_warnings = validate_imported_chapter_rewrite_output(
            output=markdown,
            original=original,
            target_title=state_chapter_title(state),
            next_chapter=state_imported_chapter(state, "imported_next_chapter"),
            user_instruction=state.get("rewrite_instruction", ""),
        )
        warnings = [*state.get("warnings", []), *validation_warnings]
        for warning in validation_warnings:
            await self.pipeline.storage_service.append_job_log(
                state["run_id"],
                f"[Warning] imported_chapter_full_rewrite: {warning}",
            )
        await self.pipeline.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name=CHAPTER_REWRITE_PLAN_ARTIFACT,
            markdown=plan_yaml,
        )
        await self.pipeline.storage_service.write_stage_markdown_artifact(
            state["run_id"],
            name=CHAPTER_REWRITE_ARTIFACT,
            markdown=markdown,
        )
        return {
            "latest_artifacts": [CHAPTER_REWRITE_ARTIFACT, CHAPTER_REWRITE_PLAN_ARTIFACT],
            "persist_payload": {
                "markdown": markdown,
                "plan_yaml": plan_yaml,
            },
            "warnings": warnings,
        }

    async def generate_selection_rewrite(self, state: NovelWorkflowState) -> str:
        current_bible = state.get("current_bible", {})
        state_for_context: NovelWorkflowState = {
            **state,
            "text_before_cursor": (
                f"{state.get('text_before_selection', '')}\n"
                f"{state.get('selected_text', '')}"
            ),
        }
        selected_context = await self.pipeline._select_writing_context(
            state_for_context,
            current_bible,
        )
        generation_profile = self.pipeline._generation_profile_obj(state)
        objective_card = build_chapter_objective_card(
            generation_profile,
            current_chapter_context=state.get("current_chapter_context", ""),
            outline_detail=selected_context.outline_detail,
        )
        system_prompt = assemble_writing_context(
            voice_profile_markdown=state.get("style_prompt"),
            story_engine_markdown=state.get("plot_prompt"),
            generation_profile=generation_profile,
            intensity_profile=build_intensity_profile(generation_profile),
            chapter_objective_card=objective_card,
            sections=WritingContextSections(
                description=state.get("project_description", ""),
                world_building=selected_context.world_building,
                characters_blueprint=selected_context.characters_blueprint,
                outline_master=selected_context.outline_master,
                outline_detail=selected_context.outline_detail,
                characters_status=selected_context.characters_status,
                runtime_state=selected_context.runtime_state,
                runtime_threads=selected_context.runtime_threads,
                story_summary=selected_context.story_summary,
                active_character_focus=selected_context.active_character_focus,
            ),
            prompt_asset_layers=state_prompt_asset_layers(state),
            length_preset=state.get("length_preset", "long"),
            content_length=state.get("total_content_length", 0),
        )
        parts: list[str] = []
        if state.get("previous_chapter_context", "").strip():
            parts.append(f"## 前序章节\n\n{state.get('previous_chapter_context', '')}")
        if state.get("current_chapter_context", "").strip():
            parts.append(f"## 当前章节\n\n{state.get('current_chapter_context', '')}")
        if selected_context.active_character_focus.strip():
            parts.append("# Active Character Focus\n\n" + selected_context.active_character_focus)
        if state.get("text_before_selection", "").strip():
            parts.append(f"## 选区前文\n\n{state.get('text_before_selection', '')[-3000:]}")
        parts.append("## 选中文本\n\n" f"{state.get('selected_text', '')}")
        if state.get("text_after_selection", "").strip():
            parts.append(f"## 选区后文\n\n{state.get('text_after_selection', '')[:3000]}")
        parts.append(
            "## 修改要求\n\n"
            f"{state.get('rewrite_instruction', '').strip() or '在不改变原意的前提下优化表达。'}\n\n"
            "只输出改写后的选中文本。不要生成选区后的内容，不要输出解释、标题、引号或 Markdown 包装。"
        )
        return await self.pipeline._call_prompt(
            system_prompt=system_prompt,
            user_context="\n\n---\n\n".join(parts),
            mode="immersion",
            prompt_stack_manifest=state_prompt_stack_manifest(state),
        )

    async def generate_chapter_enrichment_rewrite(
        self,
        state: NovelWorkflowState,
    ) -> str:
        chapter_content = self.chapter_enrichment_rewrite_source_text(state)
        if not chapter_content.strip():
            raise ValueError("当前章节正文为空，无法改写")
        if len(chapter_content) > 80_000:
            raise ValueError("当前章节过长，v1 暂不支持自动分块改写")

        current_bible = state.get("current_bible", {})
        selected_context = await self.pipeline._select_writing_context(
            {
                **state,
                "text_before_cursor": chapter_content,
                "current_chapter_context": (
                    state.get("current_chapter_context", "")
                    or chapter_content[:3000]
                ),
            },
            current_bible,
        )
        generation_profile = self.pipeline._generation_profile_obj(state)
        objective_card = build_chapter_objective_card(
            generation_profile,
            current_chapter_context=state.get("current_chapter_context", ""),
            outline_detail=selected_context.outline_detail,
        )
        system_prompt = (
            assemble_writing_context(
                voice_profile_markdown=state.get("style_prompt"),
                story_engine_markdown=state.get("plot_prompt"),
                generation_profile=generation_profile,
                intensity_profile=build_intensity_profile(generation_profile),
                chapter_objective_card=objective_card,
                sections=WritingContextSections(
                    description=state.get("project_description", ""),
                    world_building=selected_context.world_building,
                    characters_blueprint=selected_context.characters_blueprint,
                    outline_master=selected_context.outline_master,
                    outline_detail=selected_context.outline_detail,
                    characters_status=selected_context.characters_status,
                    runtime_state=selected_context.runtime_state,
                    runtime_threads=selected_context.runtime_threads,
                    story_summary=selected_context.story_summary,
                    active_character_focus=selected_context.active_character_focus,
                ),
                prompt_asset_layers=state_prompt_asset_layers(state),
                length_preset=state.get("length_preset", "long"),
                content_length=len(chapter_content),
            )
            + self.chapter_rewrite_plan_contract(
                expansion_ratio_percent=state.get("expansion_ratio_percent", 20)
            )
        )
        parts = []
        if state.get("previous_chapter_context", "").strip():
            parts.append(f"## 前序章节\n\n{state.get('previous_chapter_context', '')}")
        if state.get("current_chapter_context", "").strip():
            parts.append(f"## 当前章节定位\n\n{state.get('current_chapter_context', '')}")
        parts.append(
            "## 编号后的原章节正文\n\n"
            f"{build_numbered_chapter_rewrite_source(chapter_content)}"
        )
        parts.append(
            "## 用户自由改写指令\n\n"
            f"{state.get('rewrite_instruction', '').strip()}\n\n"
            "按上述指令改写整个章节，但输出必须只包含 YAML front matter 改写计划，不得输出改写后的完整章节。"
        )
        retry_context = self.chapter_rewrite_retry_context(state)
        if retry_context:
            parts.append(retry_context)
        return await self.pipeline._call_prompt(
            system_prompt=system_prompt,
            user_context="\n\n---\n\n".join(parts),
            mode="immersion",
            prompt_stack_manifest=state_prompt_stack_manifest(state),
        )

    async def generate_imported_chapter_full_rewrite(
        self,
        state: NovelWorkflowState,
    ) -> str:
        chapter_content = state_chapter_content(state)
        if not chapter_content.strip():
            raise ValueError("当前章节正文为空，无法改写")
        if len(chapter_content) > 80_000:
            raise ValueError("当前章节过长，v1 暂不支持自动分块改写")

        current_bible = state.get("current_bible", {})
        selected_context = await self.pipeline._select_imported_rewrite_character_context(
            state,
            current_bible,
            chapter_content,
        )
        active_character_focus = selected_context.active_character_focus.strip()
        system_prompt = build_imported_chapter_rewrite_system_prompt(
            voice_profile_markdown=state.get("style_prompt", ""),
            active_character_focus=active_character_focus,
            expansion_ratio_percent=state.get("expansion_ratio_percent", 20),
        )
        previous_chapter = state_imported_chapter(state, "imported_previous_chapter")
        next_chapter = state_imported_chapter(state, "imported_next_chapter")
        user_context = build_imported_chapter_rewrite_user_context(
            target_title=state_chapter_title(state),
            chapter_content=build_numbered_chapter_rewrite_source(chapter_content),
            previous_chapter=previous_chapter,
            next_chapter=next_chapter,
            rewrite_instruction=state.get("rewrite_instruction", ""),
            expansion_ratio_percent=state.get("expansion_ratio_percent", 20),
        )
        retry_context = self.chapter_rewrite_retry_context(state)
        if retry_context:
            user_context = f"{user_context}\n\n---\n\n{retry_context}"
        return await self.pipeline._call_prompt(
            system_prompt=system_prompt,
            user_context=user_context,
            mode="immersion",
            prompt_stack_manifest=_merge_prompt_stack_manifest(
                state_prompt_stack_manifest(state),
                build_imported_context_manifest(
                    state=state,
                    chapter_content=chapter_content,
                    previous_chapter=previous_chapter,
                    next_chapter=next_chapter,
                    voice_profile_markdown=state.get("style_prompt", ""),
                    active_character_focus=active_character_focus,
                    active_character_names=selected_context.active_character_names,
                ),
            ),
        )

    @staticmethod
    def chapter_enrichment_rewrite_source_text(state: NovelWorkflowState) -> str:
        chapter_snapshot = state.get("chapter_snapshot")
        if isinstance(chapter_snapshot, dict):
            content = chapter_snapshot.get("content", "")
            if isinstance(content, str) and content.strip():
                return content
        return state.get("selected_text", "")

    @staticmethod
    def chapter_rewrite_plan_contract(*, expansion_ratio_percent: int) -> str:
        return (
            "\n\n## 章节改写 YAML 输出硬规则\n"
            "- 你必须只输出 YAML front matter 改写计划，不得输出改写后的完整章节。\n"
            "- 输出必须以 `---` 开始并以 `---` 结束；结束后不得有任何正文、说明、Notes 或 Markdown 内容。\n"
            "- YAML 顶层只能包含 `edits`，且 `edits` 必须是非空列表。\n"
            "- 每个 edit 必须包含 `operation`、`paragraph_id`、`new_text` 三个字段。\n"
            "- `operation` 只能是 `insert_after` 或 `replace`。\n"
            "- `paragraph_id` 必须引用用户消息中给出的单个原文段落编号，例如 `P003`；不得复制原文作为 Anchor。\n"
            "- 同一个 `paragraph_id` 在一次计划中最多出现一次。\n"
            "- `new_text` 必须使用 YAML 块文本 `|-`，不能为空，可以包含一个或多个新自然段。\n"
            "- `insert_after` 表示把 `new_text` 插入到该编号段落后；`replace` 表示只替换该编号对应的一个原始自然段。\n"
            "- 不得做句子级定位，不得一次替换多个原始段落，不得引用不存在的段落编号。\n"
            "- 所有 edits 会先整体校验，再按原章节段落顺序应用；不要依赖输出顺序表达章节顺序。\n"
            f"- 合成后的净增长至少达到原文字数的 {expansion_ratio_percent}% 目标的 80%；允许超出目标上限。\n"
            "\n"
            "格式示例：\n"
            "---\n"
            "edits:\n"
            "  - operation: insert_after\n"
            "    paragraph_id: P003\n"
            "    new_text: |-\n"
            "      <one or more new paragraphs>\n"
            "  - operation: replace\n"
            "    paragraph_id: P008\n"
            "    new_text: |-\n"
            "      <rewritten paragraph text>\n"
            "---\n"
        )

    async def generate_valid_chapter_rewrite_plan(
        self,
        *,
        state: NovelWorkflowState,
        original: str,
        generator: Callable[[NovelWorkflowState], Awaitable[str]],
    ) -> tuple[str, str]:
        retry_invalid_output: str | None = None
        retry_validation_error: str | None = None
        for attempt in range(_CHAPTER_REWRITE_PATCH_MAX_ATTEMPTS):
            attempt_state = state
            if retry_invalid_output is not None and retry_validation_error is not None:
                attempt_state = {
                    **state,
                    "chapter_rewrite_retry_invalid_output": retry_invalid_output,
                    "chapter_rewrite_retry_validation_error": retry_validation_error,
                }
            plan_yaml = await generator(attempt_state)
            try:
                markdown = self.synthesize_chapter_rewrite(
                    original=original,
                    plan_yaml=plan_yaml,
                    expansion_ratio_percent=state.get("expansion_ratio_percent", 20),
                )
            except ValueError as exc:
                if attempt == _CHAPTER_REWRITE_PATCH_MAX_ATTEMPTS - 1:
                    raise
                retry_invalid_output = plan_yaml
                retry_validation_error = str(exc)
                continue
            return plan_yaml.strip(), markdown
        raise RuntimeError("unreachable chapter rewrite plan retry state")

    @staticmethod
    def chapter_rewrite_retry_context(state: NovelWorkflowState) -> str:
        invalid_output = (state.get("chapter_rewrite_retry_invalid_output") or "").strip()
        validation_error = (
            state.get("chapter_rewrite_retry_validation_error") or ""
        ).strip()
        if not invalid_output or not validation_error:
            return ""
        invalid_excerpt = invalid_output[:_CHAPTER_REWRITE_RETRY_OUTPUT_CHARS]
        if len(invalid_output) > _CHAPTER_REWRITE_RETRY_OUTPUT_CHARS:
            invalid_excerpt = f"{invalid_excerpt}\n...[truncated]"
        return (
            "## 上一次 YAML 改写计划校验失败（必须修正后重试）\n\n"
            f"校验错误：{validation_error}\n\n"
            "上一次无效输出（可能已截断）：\n\n"
            f"{invalid_excerpt}\n\n"
            "重试要求：重新输出完整 YAML front matter，不要只输出局部修复；"
            "`edits` 必须是非空列表，每个 edit 必须独立包含 operation、paragraph_id、new_text；"
            "paragraph_id 必须引用编号后的原章节正文中的一个段落 ID，且不能重复。"
        )

    @staticmethod
    def synthesize_chapter_rewrite(
        *,
        original: str,
        plan_yaml: str,
        expansion_ratio_percent: int,
    ) -> str:
        return synthesize_chapter_rewrite_plan(
            original=original,
            front_matter_markdown=plan_yaml,
            expansion_ratio_percent=expansion_ratio_percent,
        )


def _merge_prompt_stack_manifest(
    prompt_stack_manifest: dict | None,
    imported_context_manifest: dict[str, Any],
) -> dict[str, Any]:
    if prompt_stack_manifest is None:
        return {"imported_rewrite_context": imported_context_manifest}
    return {
        **prompt_stack_manifest,
        "imported_rewrite_context": imported_context_manifest,
    }
