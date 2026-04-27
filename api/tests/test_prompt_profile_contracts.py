from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.api.assemblers import build_job_detail_response, build_plot_job_detail_response
from app.schemas.novel_workflows import NovelWorkflowCreateRequest
from app.schemas.plot_profiles import PlotProfileCreate
from app.schemas.projects import ProjectCreate, ProjectResponse, ProjectUpdate
from app.schemas.style_profiles import StyleProfileCreate


def _load_prompt_profile_symbols() -> dict[str, object]:
    module = importlib.import_module("app.schemas.prompt_profiles")
    return {
        name: getattr(module, name)
        for name in (
            "ChapterObjectiveCard",
            "GenerationProfile",
            "IntensityProfile",
            "PlotWritingGuideProfile",
            "StoryEngineProfile",
            "VoiceProfile",
        )
    }


def _build_generation_profile():
    GenerationProfile = _load_prompt_profile_symbols()["GenerationProfile"]
    return GenerationProfile(
        genre_mother="xianxia",
        desire_overlays=["harem_collect"],
        intensity_level="explicit",
        pov_mode="limited_third",
        morality_axis="ruthless_growth",
        pace_density="fast",
    )


def test_prompt_profile_schemas_expose_exact_required_fields() -> None:
    symbols = _load_prompt_profile_symbols()
    VoiceProfile = symbols["VoiceProfile"]
    PlotWritingGuideProfile = symbols["PlotWritingGuideProfile"]
    StoryEngineProfile = symbols["StoryEngineProfile"]
    IntensityProfile = symbols["IntensityProfile"]
    ChapterObjectiveCard = symbols["ChapterObjectiveCard"]
    voice = VoiceProfile(
        common_expressions="高频口头禅以短反问和口语感叹推进。",
        sentence_patterns="短句抢拍，长句用于补充判断。",
        lexical_preferences="混用现代管理词、网络口语和古典四字格。",
        sentence_construction="句首常直接落判断，句尾用反问或短断语收束。",
        personal_scene_clues="生活线索弱，更多来自商业运营和组织管理语境。",
        domain_regional_lexicon="行业词偏运营、渠道、成本收益；地域词不明显。",
        natural_irregularities="允许省略、跳接、省略号和破折号制造停顿。",
        avoided_patterns="少用解释性开场和总结升华。",
        metaphors_imagery="意象偏月色、玉色、视线、掌心、清冷院落。",
        logic_and_emotion="常按观察、质疑、类比、结论推进心理判断。",
        dialogue_modes="对白以抢拍反问、调侃揭短和上位压迫为主。",
        values_motifs="反复强调效率、交易、掌控和关系博弈。",
    )
    story = StoryEngineProfile(
        genre_mother="xianxia",
        drive_axes=["升级", "掠夺", "关系占有"],
        payoff_objects=["力量", "名分", "资源"],
        pressure_formulas=["宗门压制 -> 反制夺位"],
        relation_roles=["奖励源", "压迫源", "猎物"],
        scene_verbs=["入局", "压制", "试探", "收割"],
        hook_recipes=["半兑现后立刻追加新压力"],
        anti_drift_guardrails=["不要退化成纯气氛描写"],
    )
    plot_guide = PlotWritingGuideProfile(
        core_plot_formula=["用压力迫使主角行动。"],
        chapter_progression_loop=["目标 -> 阻碍 -> 行动 -> 小兑现 -> 新压力。"],
        scene_construction_rules=["每个场景必须改变局面。"],
        setup_and_payoff_rules=["伏笔必须参与行动兑现。"],
        payoff_and_tension_rhythm=["半兑现后追加更大压力。"],
        side_plot_usage=["支线必须回流主线。"],
        hook_recipes=["胜利后揭示代价。"],
        anti_drift_rules=["不要复述样本剧情。"],
    )
    intensity = IntensityProfile(
        intensity_level="explicit",
        desire_overlays=["harem_collect", "dominance_capture"],
        expression_focus=["占有欲", "边界试探", "身体感官"],
        boundary_rules=["未成年相关绝对移除"],
        soft_conflicts=["催眠控制与 plot_only 档位不协调"],
    )
    chapter = ChapterObjectiveCard(
        chapter_goal="seduce",
        payoff_target="relationship",
        pressure_source="宗门考核与女主名分压力",
        relationship_delta="从试探推进到默认暧昧绑定",
        adult_expression_mode="explicit",
        hook_type="half_payoff_then_backlash",
    )

    assert set(voice.model_dump().keys()) == {
        "common_expressions",
        "sentence_patterns",
        "lexical_preferences",
        "sentence_construction",
        "personal_scene_clues",
        "domain_regional_lexicon",
        "natural_irregularities",
        "avoided_patterns",
        "metaphors_imagery",
        "logic_and_emotion",
        "dialogue_modes",
        "values_motifs",
    }
    assert set(story.model_dump().keys()) == {
        "genre_mother",
        "drive_axes",
        "payoff_objects",
        "pressure_formulas",
        "relation_roles",
        "scene_verbs",
        "hook_recipes",
        "anti_drift_guardrails",
    }
    assert set(plot_guide.model_dump().keys()) == {
        "core_plot_formula",
        "chapter_progression_loop",
        "scene_construction_rules",
        "setup_and_payoff_rules",
        "payoff_and_tension_rhythm",
        "side_plot_usage",
        "hook_recipes",
        "anti_drift_rules",
    }
    assert set(intensity.model_dump().keys()) == {
        "intensity_level",
        "desire_overlays",
        "expression_focus",
        "boundary_rules",
        "soft_conflicts",
    }
    assert set(chapter.model_dump().keys()) == {
        "chapter_goal",
        "payoff_target",
        "pressure_source",
        "relationship_delta",
        "adult_expression_mode",
        "hook_type",
    }


def test_generation_profile_enforces_declared_enums() -> None:
    symbols = _load_prompt_profile_symbols()
    GenerationProfile = symbols["GenerationProfile"]
    IntensityProfile = symbols["IntensityProfile"]

    with pytest.raises(ValidationError):
        GenerationProfile(
            genre_mother="western_fantasy",
            desire_overlays=[],
            intensity_level="explicit",
            pov_mode="limited_third",
            morality_axis="ruthless_growth",
            pace_density="fast",
        )

    with pytest.raises(ValidationError):
        IntensityProfile(
            intensity_level="nsfw_max",
            desire_overlays=[],
            expression_focus=["压迫"],
            boundary_rules=["未成年相关绝对移除"],
            soft_conflicts=[],
        )


def test_project_and_novel_workflow_requests_accept_generation_profile() -> None:
    generation_profile = _build_generation_profile()

    create_payload = ProjectCreate(
        name="新书",
        default_provider_id="provider-1",
        generation_profile=generation_profile,
    )
    update_payload = ProjectUpdate(generation_profile=generation_profile)
    workflow_payload = NovelWorkflowCreateRequest(
        intent_type="continuation_write",
        text_before_cursor="他看着她，没有说话。",
        generation_profile=generation_profile,
    )
    response = ProjectResponse(
        id="project-1",
        name="新书",
        description="",
        status="draft",
        default_provider_id="provider-1",
        default_model="model-1",
        style_profile_id="style-1",
        plot_profile_id="plot-1",
        generation_profile=generation_profile,
        length_preset="short",
        auto_sync_memory=False,
        archived_at=None,
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
        provider={
            "id": "provider-1",
            "label": "primary",
            "base_url": "https://example.invalid/v1",
            "default_model": "model-1",
            "is_enabled": True,
        },
    )

    assert create_payload.generation_profile == generation_profile
    assert update_payload.generation_profile == generation_profile
    assert workflow_payload.generation_profile == generation_profile
    assert response.generation_profile == generation_profile


def test_style_and_plot_profile_payloads_accept_new_markdown_fields_without_legacy_prompt_pack() -> None:
    style_payload = StyleProfileCreate(
        job_id="job-1",
        style_name="冷白",
        voice_profile_markdown="# Voice Profile\n## 3.1 口头禅与常用表达\n- 执行规则：短句推进。\n",
    )
    plot_payload = PlotProfileCreate(
        job_id="job-1",
        plot_name="宗门夺位",
        story_engine_markdown="# Plot Writing Guide\n## Core Plot Formula\n- 用压力迫使主角行动。\n",
    )

    assert style_payload.voice_profile_markdown
    assert plot_payload.story_engine_markdown


def test_style_job_detail_exposes_voice_profile_fields_from_runtime_payload() -> None:
    response = build_job_detail_response(
        SimpleNamespace(
            id="job-1",
            style_name="冷白",
            provider_id="provider-1",
            model_name="model-1",
            status="succeeded",
            stage=None,
            error_message=None,
            started_at=None,
            completed_at=None,
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
            pause_requested_at=None,
            provider=SimpleNamespace(
                id="provider-1",
                label="primary",
                base_url="https://example.invalid/v1",
                default_model="model-1",
                is_enabled=True,
            ),
            sample_file=SimpleNamespace(
                id="sample-1",
                original_filename="sample.txt",
                content_type="text/plain",
                byte_size=12,
                character_count=12,
                checksum_sha256="a" * 64,
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
            ),
            style_profile_id=None,
            style_profile=None,
            analysis_meta_payload={
                "source_filename": "sample.txt",
                "model_name": "model-1",
                "text_type": "章节正文",
                "has_timestamps": False,
                "has_speaker_labels": False,
                "has_noise_markers": False,
                "uses_batch_processing": False,
                "location_indexing": "章节或段落位置",
                "chunk_count": 1,
            },
            analysis_report_payload="# 执行摘要\n冷白。\n",
            voice_profile_payload=(
                "# Voice Profile\n"
                "## 3.1 口头禅与常用表达\n- 执行规则：短句推进。\n"
                "## 3.2 固定句式与节奏偏好\n- 执行规则：长短句交替。\n"
            ),
        )
    )

    assert response.voice_profile_markdown.startswith("# Voice Profile")
    assert response.voice_profile_payload.common_expressions
    assert response.voice_profile_payload.sentence_patterns


def test_plot_job_detail_exposes_story_engine_fields_from_runtime_payload() -> None:
    response = build_plot_job_detail_response(
        SimpleNamespace(
            id="job-1",
            plot_name="宗门夺位",
            provider_id="provider-1",
            model_name="model-1",
            status="succeeded",
            stage=None,
            error_message=None,
            started_at=None,
            completed_at=None,
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
            pause_requested_at=None,
            provider=SimpleNamespace(
                id="provider-1",
                label="primary",
                base_url="https://example.invalid/v1",
                default_model="model-1",
                is_enabled=True,
            ),
            sample_file=SimpleNamespace(
                id="sample-1",
                original_filename="sample.txt",
                content_type="text/plain",
                byte_size=12,
                character_count=12,
                checksum_sha256="a" * 64,
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
            ),
            plot_profile_id=None,
            plot_profile=None,
            analysis_report_payload="# 执行摘要\n高压推进。\n",
            story_engine_payload=(
                "# Plot Writing Guide\n"
                "## Core Plot Formula\n- 用压力迫使主角行动。\n"
                "## Chapter Progression Loop\n- 目标 -> 阻碍 -> 行动 -> 小兑现 -> 新压力。\n"
            ),
            plot_skeleton_payload="# 全书骨架\n启动期\n",
        )
    )

    assert response.story_engine_markdown.startswith("# Plot Writing Guide")
    assert response.story_engine_payload.core_plot_formula
    assert response.story_engine_payload.chapter_progression_loop
