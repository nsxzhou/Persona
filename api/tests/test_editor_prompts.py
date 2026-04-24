from __future__ import annotations

import pytest
from pydantic import TypeAdapter
from app.services.editor_prompts import (
    build_beat_expand_system_prompt,
    build_beat_expand_user_message,
    build_beat_generate_system_prompt,
    build_beat_generate_user_message,
    build_bible_update_system_prompt,
    build_bible_update_user_message,
    build_concept_generate_system_prompt,
    build_concept_generate_user_message,
    build_section_system_prompt,
    build_section_user_message,
    build_volume_chapters_system_prompt,
    build_volume_chapters_user_message,
    build_volume_generate_system_prompt,
    build_volume_generate_user_message,
)
from app.schemas.editor import (
    BeatExpandRequest,
    BeatGenerateRequest,
    BibleUpdateRequest,
    SectionGenerateRequest,
    VolumeChaptersRequest,
    VolumeGenerateRequest,
)
from app.schemas.projects import ConceptGenerateRequest


def test_world_building_prompt_uses_core_scaffold_and_conditional_modules() -> None:
    prompt = build_section_system_prompt("world_building", length_preset="long")

    assert "生成一份足以支撑人物、冲突和前期展开的必要设定" in prompt
    assert "若简介未明确写出超自然，则默认不存在超自然" in prompt
    assert "只保留当前故事真正需要的模块" in prompt
    assert "1. **时代与秩序**" in prompt
    assert "2. **当前局势与核心冲突土壤**" in prompt
    assert "3. **主角当前处境与约束**" in prompt
    assert "仅在确有需要时，才补充下列可选模块" in prompt
    assert "特殊设定（仅简介明示时）" in prompt
    assert "主要势力" in prompt
    assert "关键前史" in prompt
    assert "活动空间与扩展方向" in prompt
    assert "资源与利益流动" in prompt
    assert "隐秘规则/禁忌" not in prompt


def test_world_building_prompt_prefers_grounded_identity_swap_reading() -> None:
    prompt = build_section_system_prompt("world_building", length_preset="long")

    assert "借皮囊/借壳/替身/换身份/李代桃僵" in prompt
    assert "默认优先按现实权谋或身份操作理解" in prompt
    assert "相貌相似、冒名顶替、伪造文书、家族关系运作、替考替身、身份植入" in prompt
    assert "不得把上述表达解释成世界规则、禁忌体系或异常机制" in prompt


def test_world_building_prompt_includes_grounded_and_supernatural_examples() -> None:
    prompt = build_section_system_prompt("world_building", length_preset="medium")

    assert "示例（应按现实权谋理解）" in prompt
    assert "门阀夫人要借他皮囊一用" in prompt
    assert "应理解为身份顶替、冒名入局、关系运作或李代桃僵" in prompt
    assert "示例（才允许进入“特殊设定”）" in prompt
    assert "她需借尸还魂，必须在子时行夺舍仪式" in prompt
    assert "这类内容才允许扩写为超自然或异常机制" in prompt


@pytest.mark.parametrize("length_preset", ["short", "medium", "long"])
def test_world_building_prompt_removes_hard_coded_setting_checklist(
    length_preset: str,
) -> None:
    prompt = build_section_system_prompt("world_building", length_preset=length_preset)

    assert "必须覆盖以下六个维度" not in prompt
    assert "至少 3 个互相制衡的势力" not in prompt
    assert "至少 6 级" not in prompt
    assert "力量/修炼体系 3-4 级即可" not in prompt
    assert "力量体系 4-5 级，势力 2-3 个" not in prompt
    assert "经济必须与力量等级挂钩" not in prompt


def test_world_building_prompt_explicitly_blocks_over_generation() -> None:
    prompt = build_section_system_prompt("world_building", length_preset="medium")

    assert "暧昧、诡秘、留白不等于存在隐藏机制" in prompt
    assert "历史、权谋、现实、悬疑等题材，不要默认生成公开修炼体系或全民力量系统" in prompt
    assert "历史、权谋、现实题材，不得因为简介带有诡异感、暧昧感或留白，就自行补出秘密体系、禁忌机制或异常规则" in prompt
    assert "资源争夺并非主线时，不要专门发明货币、修炼材料、交易媒介" in prompt
    assert "不要为了显得完整而补完世界" in prompt
    assert "不要发明暂时不会进入剧情的设定" in prompt
    assert "若某条设定不会改变主角选择、冲突强度或后续兑现路径，就不要展开" in prompt
    assert "不要拿设定规模、世界分层或古老秘闻数量冒充故事深度或爽点" in prompt


def test_adjacent_prompts_preserve_grounded_reading() -> None:
    characters_prompt = build_section_system_prompt("characters", length_preset="long")
    outline_prompt = build_section_system_prompt("outline_master", length_preset="long")

    assert "沿用世界观已确定的题材解释，不得把现实权谋误写为超自然机制或秘密体系" in characters_prompt
    assert "沿用世界观已确定的题材解释，不得把现实权谋误写为超自然机制或秘密体系" in outline_prompt


def test_creative_planning_sections_prefer_useful_detail_over_maximal_fill() -> None:
    prompts = [
        build_section_system_prompt("world_building", length_preset="long"),
        build_section_system_prompt("characters", length_preset="long"),
        build_section_system_prompt("outline_master", length_preset="long"),
        build_section_system_prompt("outline_detail", length_preset="long"),
    ]

    for prompt in prompts:
        assert "具体且有用" in prompt
        assert "内容丰富具体" not in prompt


def test_bible_generation_sections_inject_plot_prompt_after_style_prompt() -> None:
    prompt = build_section_system_prompt(
        "world_building",
        style_prompt="# Style Prompt\n风格约束\n",
        plot_prompt="# Plot Prompt\n情节约束\n",
        length_preset="long",
    )

    assert "# Style Prompt\n风格约束" in prompt
    assert "# Plot Prompt\n情节约束" in prompt
    assert prompt.index("# Style Prompt\n风格约束") < prompt.index("# Plot Prompt\n情节约束")
    assert "Plot 是结构约束，不是内容模板" in prompt

    characters_prompt = build_section_system_prompt(
        "characters",
        style_prompt="# Style Prompt\n风格约束\n",
        plot_prompt="# Plot Prompt\n情节约束\n",
        length_preset="long",
    )
    assert "# Plot Prompt\n情节约束" in characters_prompt
    assert "不得照搬样本角色、设定、事件" in characters_prompt


def test_character_prompt_prioritizes_conflict_function_over_packaging() -> None:
    prompt = build_section_system_prompt("characters", length_preset="long")

    assert "角色信息优先回答以下问题" in prompt
    assert "他是谁，为什么此刻会入局" in prompt
    assert "他如何卡住主角，或为什么能帮主角破局" in prompt
    assert "主角能利用、交换、规避或反制他的点是什么" in prompt
    assert "角色弧光" not in prompt
    assert "反差设计" not in prompt
    assert "阶段性反派（至少 1 个）" not in prompt


def test_outline_master_prompt_organizes_progress_around_main_pleasure_axis() -> None:
    prompt = build_section_system_prompt("outline_master", length_preset="long")

    assert "先判断这本书当前真正靠什么让人继续看下去" in prompt
    assert "围绕同一条主爽点主线组织推进" in prompt
    assert "不要为了拉大规模而额外铺地图、体系、势力层级" in prompt
    assert "地图换挡" not in prompt
    assert "阶段 Boss/核心对手" not in prompt


def test_outline_master_prompt_injects_plot_prompt_after_style_prompt() -> None:
    prompt = build_section_system_prompt(
        "outline_master",
        style_prompt="# Style Prompt\n风格约束\n",
        plot_prompt="# Plot Prompt\n情节约束\n",
        length_preset="long",
    )

    assert "# Style Prompt\n风格约束" in prompt
    assert "# Plot Prompt\n情节约束" in prompt
    assert prompt.index("# Style Prompt\n风格约束") < prompt.index("# Plot Prompt\n情节约束")
    assert prompt.index("# Plot Prompt\n情节约束") < prompt.index("你是一位起点白金作家")
    assert "Plot 是结构约束，不是内容模板" in prompt


def test_outline_detail_prompt_prefers_driving_endings_over_forced_hooks() -> None:
    prompt = build_section_system_prompt("outline_detail", length_preset="long")

    assert "章节末推动点" in prompt
    assert "可以是悬念、反转、新压力、关系变化或阶段性兑现" in prompt
    assert "不必每章硬凹爆点" in prompt
    assert "每章结尾必须有一个让读者想翻下一章的悬念或爆点" not in prompt


def test_volume_generate_prompt_injects_plot_prompt_after_style_prompt() -> None:
    prompt = build_volume_generate_system_prompt(
        length_preset="long",
        style_prompt="# Style Prompt\n风格约束\n",
        plot_prompt="# Plot Prompt\n情节约束\n",
    )

    assert "# Style Prompt\n风格约束" in prompt
    assert "# Plot Prompt\n情节约束" in prompt
    assert prompt.index("# Style Prompt\n风格约束") < prompt.index("# Plot Prompt\n情节约束")
    assert prompt.index("# Plot Prompt\n情节约束") < prompt.index("你是一位起点白金作家")


def test_volume_chapters_prompt_injects_plot_prompt_after_style_prompt() -> None:
    prompt = build_volume_chapters_system_prompt(
        style_prompt="# Style Prompt\n风格约束\n",
        plot_prompt="# Plot Prompt\n情节约束\n",
    )

    assert "# Style Prompt\n风格约束" in prompt
    assert "# Plot Prompt\n情节约束" in prompt
    assert prompt.index("# Style Prompt\n风格约束") < prompt.index("# Plot Prompt\n情节约束")
    assert prompt.index("# Plot Prompt\n情节约束") < prompt.index("你是一位起点白金作家")


def test_outline_detail_prompt_injects_plot_prompt_after_style_prompt() -> None:
    prompt = build_section_system_prompt(
        "outline_detail",
        style_prompt="# Style Prompt\n风格约束\n",
        plot_prompt="# Plot Prompt\n情节约束\n",
        length_preset="long",
    )

    assert "# Style Prompt\n风格约束" in prompt
    assert "# Plot Prompt\n情节约束" in prompt
    assert prompt.index("# Style Prompt\n风格约束") < prompt.index("# Plot Prompt\n情节约束")
    assert prompt.index("# Plot Prompt\n情节约束") < prompt.index("你是一位起点白金作家")


def test_identity_swap_description_regression_is_passed_with_grounded_guardrails() -> None:
    description = (
        "好消息：穿成解元，才华横溢。坏消息：刚被诬下狱，择日问斩。"
        "绝境中，门阀望族的美艳夫人，要借我皮囊一用！"
    )

    user_message = build_section_user_message(
        "world_building",
        {
            "description": description,
            "world_building": "",
            "characters": "",
            "outline_master": "",
            "outline_detail": "",
            "runtime_state": "",
            "runtime_threads": "",
        },
    )
    system_prompt = build_section_system_prompt("world_building", length_preset="long")

    assert description in user_message
    assert "借皮囊/借壳/替身/换身份/李代桃僵" in system_prompt
    assert "默认优先按现实权谋或身份操作理解" in system_prompt


def test_bible_update_prompt_uses_scope_aware_check_content_label() -> None:
    user_message = build_bible_update_user_message(
        current_runtime_state="旧状态",
        current_runtime_threads="旧伏笔",
        content_to_check="这是整章正文",
        sync_scope="chapter_full",
    )

    assert "## 当前运行时状态\n\n旧状态" in user_message
    assert "## 当前伏笔与线索追踪\n\n旧伏笔" in user_message
    assert "## 待检查正文（整章）\n\n这是整章正文" in user_message
    assert "## 本次新生成的正文" not in user_message


def test_bible_update_system_prompt_forbids_placeholder_references() -> None:
    system_prompt = build_bible_update_system_prompt()

    assert "输出两个区块的完整最终版本（可直接替换旧文档）" in system_prompt
    assert "严禁使用“保留原有/同上/沿用旧内容/并追加以下/其余不变”等指代或占位语" in system_prompt
    assert "新增事件、角色、伏笔必须与旧信息合并后完整输出，不能只输出增量" in system_prompt
    assert "- 保留原有内容中仍然有效的信息" not in system_prompt


def test_bible_update_system_prompt_prefers_minimal_persistent_memory() -> None:
    system_prompt = build_bible_update_system_prompt()

    assert "只保留会影响后续章节的持续性变化" in system_prompt
    assert "稳定事实变化" in system_prompt
    assert "关系变化" in system_prompt
    assert "未回收线索或新风险" in system_prompt
    assert "优先判断是否无需更新" in system_prompt
    assert "不要把本章剧情改写成摘要" in system_prompt


def test_concept_generate_prompt_prefers_compact_project_intro_over_long_packaging() -> None:
    prompt = build_concept_generate_system_prompt()

    assert "每个概念包含标题和一段可直接用作项目简介的简介" in prompt
    assert "字数控制在 150-260 字左右" in prompt
    assert "按 1-3 个自然段组织" in prompt
    assert "宁可短而抓人，也不要为了显得厚重而写成长简介" in prompt
    assert "一段可直接用作项目简介的长简介" not in prompt


def test_concept_generate_prompt_uses_shared_story_spine_strategy() -> None:
    prompt = build_concept_generate_system_prompt()

    assert "共享同一故事主轴" in prompt
    assert "不能写成三本完全不同的小说" in prompt
    assert "差异优先体现在主角切口、局势压力、关系张力、破局手段或兑现方式" in prompt
    assert "不要为了拉开差异，硬把同一主轴写成更大的体系、更多的势力或更高的世界层级" in prompt
    assert "世界展开规模" not in prompt


def test_concept_generate_prompt_removes_fixed_three_lane_labels() -> None:
    prompt = build_concept_generate_system_prompt()

    assert "番茄脑洞/情绪流" not in prompt
    assert "起点世界/悬念流" not in prompt
    assert "反差人设流" not in prompt


def test_concept_generate_prompt_requires_genre_sensitive_opening_and_novel_intro_tone() -> None:
    prompt = build_concept_generate_system_prompt()

    assert "按题材决定是否使用短标签开头" in prompt
    assert "像小说简介，不像广告投流文案" in prompt
    assert "不要空泛开场" in prompt
    assert "不要把简介写成金句合集" in prompt


def test_concept_generate_prompt_uses_examples_without_allowing_example_copy() -> None:
    prompt = build_concept_generate_system_prompt()

    assert "仅学习标题气质、简介节奏与卖点组织方式" in prompt
    assert "不要照搬示例中的设定、身份、名词、人物关系和具体桥段" in prompt
    assert "标题参考气质" in prompt


def test_creative_section_prompts_adopt_qidian_author_persona() -> None:
    world_building_prompt = build_section_system_prompt("world_building", length_preset="long")
    characters_prompt = build_section_system_prompt("characters", length_preset="long")
    outline_prompt = build_section_system_prompt("outline_master", length_preset="long")

    assert "起点白金作家" in world_building_prompt
    assert "起点白金作家" in characters_prompt
    assert "起点白金作家" in outline_prompt
    assert "正在帮助作者构建" not in world_building_prompt
    assert "小说策划编辑" not in world_building_prompt


def test_volume_prompts_use_qidian_planning_persona() -> None:
    volume_prompt = build_volume_generate_system_prompt()
    chapters_prompt = build_volume_chapters_system_prompt()

    assert "起点白金作家" in volume_prompt
    assert "分卷规划" in volume_prompt
    assert "起点白金作家" in chapters_prompt
    assert "章节细纲" in chapters_prompt
    assert "小说策划编辑" not in volume_prompt
    assert "正在帮助作者" not in chapters_prompt


def test_beat_prompts_use_tomato_author_persona() -> None:
    beat_generate_prompt = build_beat_generate_system_prompt()
    beat_expand_prompt = build_beat_expand_system_prompt()

    assert "番茄金番作家" in beat_generate_prompt
    assert "番茄金番作家" in beat_expand_prompt
    assert "小说执笔者" not in beat_expand_prompt
    assert "正在帮助作者" not in beat_generate_prompt


def test_bible_update_prompt_uses_serial_author_maintenance_persona() -> None:
    prompt = build_bible_update_system_prompt()

    assert "长期连载中的成熟作者" in prompt
    assert "维护自己的角色状态、设定备忘与伏笔追踪" in prompt
    assert "设定维护助手" not in prompt


def test_creative_fixed_prompts_remove_old_external_helper_language() -> None:
    prompts = [
        build_section_system_prompt("world_building", length_preset="long"),
        build_volume_generate_system_prompt(),
        build_volume_chapters_system_prompt(),
        build_beat_generate_system_prompt(),
        build_beat_expand_system_prompt(),
        build_bible_update_system_prompt(),
    ]

    for prompt in prompts:
        assert "资深的小说策划编辑" not in prompt
        assert "正在帮助作者" not in prompt
        assert "设定维护助手" not in prompt
        assert "小说执笔者" not in prompt


def test_section_generate_request_only_uses_description_field() -> None:
    adapter = TypeAdapter(SectionGenerateRequest)

    from_description = adapter.validate_python({
        "section": "world_building",
        "description": "新的简介",
    })
    from_inspiration_only = adapter.validate_python({
        "section": "world_building",
        "inspiration": "旧字段",
    })

    assert from_description.description == "新的简介"
    assert from_inspiration_only.description == ""


# --------------------------------------------------------------------------- #
#  Regeneration with optional feedback                                         #
# --------------------------------------------------------------------------- #


_REGEN_MARKER = "## 重新生成指令"


@pytest.mark.parametrize(
    "system_builder,kwargs",
    [
        (build_concept_generate_system_prompt, {}),
        (build_section_system_prompt, {"section": "world_building"}),
        (build_volume_generate_system_prompt, {}),
        (build_volume_chapters_system_prompt, {}),
        (build_bible_update_system_prompt, {}),
        (build_beat_generate_system_prompt, {}),
        (build_beat_expand_system_prompt, {}),
    ],
)
def test_system_prompts_include_regeneration_guidance_only_when_requested(
    system_builder, kwargs,
) -> None:
    default_prompt = system_builder(**kwargs)
    regen_prompt = system_builder(regenerating=True, **kwargs)

    assert _REGEN_MARKER not in default_prompt
    assert _REGEN_MARKER in regen_prompt
    assert "【用户意见】" in regen_prompt
    assert "以下方【上一版结果】为基础进行修订" in regen_prompt


def test_section_user_message_appends_previous_output_and_user_feedback() -> None:
    message = build_section_user_message(
        "world_building",
        {
            "description": "简介文本",
            "world_building": "",
            "characters": "",
            "outline_master": "",
            "outline_detail": "",
            "runtime_state": "",
            "runtime_threads": "",
        },
        previous_output="旧世界观草稿",
        user_feedback="更阴郁",
    )

    assert "## 上一版结果\n\n旧世界观草稿" in message
    assert "## 用户意见（本次必须遵循）\n\n更阴郁" in message


def test_concept_user_message_appends_regeneration_context() -> None:
    message = build_concept_generate_user_message(
        "灵感",
        3,
        previous_output="[{\"title\":\"A\"}]",
        user_feedback="标题更短",
    )

    assert "请根据以下灵感描述生成 3 个小说概念" in message
    assert "## 上一版结果" in message
    assert "[{\"title\":\"A\"}]" in message
    assert "## 用户意见（本次必须遵循）" in message
    assert "标题更短" in message


def test_volume_user_message_appends_regeneration_context() -> None:
    message = build_volume_generate_user_message(
        "## 总纲内容",
        previous_output="旧分卷",
        user_feedback="再多一卷",
    )

    assert "## 总纲内容" in message
    assert "## 上一版结果\n\n旧分卷" in message
    assert "## 用户意见（本次必须遵循）\n\n再多一卷" in message


def test_volume_chapters_user_message_appends_regeneration_context() -> None:
    message = build_volume_chapters_user_message(
        "总纲",
        "卷一",
        "字数 0-10万",
        "",
        previous_output="旧章节列表",
        user_feedback="减少支线",
    )

    assert "## 上一版结果\n\n旧章节列表" in message
    assert "## 用户意见（本次必须遵循）\n\n减少支线" in message
    assert "请为当前卷设计章节细纲：" in message


def test_bible_update_user_message_appends_regeneration_context() -> None:
    message = build_bible_update_user_message(
        current_runtime_state="状态",
        current_runtime_threads="伏笔",
        content_to_check="正文",
        sync_scope="chapter_full",
        previous_output="旧建议",
        user_feedback="保留更多关系线",
    )

    assert "## 上一版结果\n\n旧建议" in message
    assert "## 用户意见（本次必须遵循）\n\n保留更多关系线" in message


def test_beat_generate_user_message_appends_regeneration_context() -> None:
    message = build_beat_generate_user_message(
        text_before_cursor="前文",
        outline_detail="",
        runtime_state="",
        runtime_threads="",
        num_beats=5,
        previous_output="[\"旧拍1\",\"旧拍2\"]",
        user_feedback="节奏更快",
    )

    assert "## 上一版结果" in message
    assert "旧拍1" in message
    assert "## 用户意见（本次必须遵循）\n\n节奏更快" in message
    assert message.index("## 上一版结果") < message.index("请生成 5 个节拍：")


def test_beat_expand_user_message_appends_regeneration_context() -> None:
    message = build_beat_expand_user_message(
        text_before_cursor="前文",
        beat="一拍",
        beat_index=0,
        total_beats=3,
        preceding_beats_prose="",
        outline_detail="",
        runtime_state="",
        runtime_threads="",
        previous_output="旧正文段",
        user_feedback="少对话多动作",
    )

    assert "## 上一版结果\n\n旧正文段" in message
    assert "## 用户意见（本次必须遵循）\n\n少对话多动作" in message


def test_user_messages_omit_regeneration_sections_when_fields_are_none() -> None:
    concept_msg = build_concept_generate_user_message("灵感", 2)
    section_msg = build_section_user_message(
        "world_building",
        {
            "description": "",
            "world_building": "",
            "characters": "",
            "outline_master": "",
            "outline_detail": "",
            "runtime_state": "",
            "runtime_threads": "",
        },
    )
    volume_msg = build_volume_generate_user_message("总纲")

    for msg in (concept_msg, section_msg, volume_msg):
        assert "## 上一版结果" not in msg
        assert "## 用户意见" not in msg


def test_user_messages_ignore_empty_whitespace_only_regeneration_fields() -> None:
    message = build_concept_generate_user_message(
        "灵感",
        2,
        previous_output="   ",
        user_feedback="\n\t",
    )

    assert "## 上一版结果" not in message
    assert "## 用户意见" not in message


@pytest.mark.parametrize(
    "model_cls,base_payload",
    [
        (
            SectionGenerateRequest,
            {"section": "world_building"},
        ),
        (
            BibleUpdateRequest,
            {"content_to_check": "正文", "sync_scope": "chapter_full"},
        ),
        (
            BeatGenerateRequest,
            {"text_before_cursor": "前文"},
        ),
        (
            BeatExpandRequest,
            {
                "text_before_cursor": "前文",
                "beat": "一拍",
                "beat_index": 0,
                "total_beats": 3,
            },
        ),
        (VolumeChaptersRequest, {"volume_index": 0}),
        (VolumeGenerateRequest, {}),
        (
            ConceptGenerateRequest,
            {"inspiration": "灵感", "provider_id": "p-1"},
        ),
    ],
)
def test_request_schemas_default_regeneration_fields_to_none(
    model_cls, base_payload,
) -> None:
    adapter = TypeAdapter(model_cls)
    parsed = adapter.validate_python(base_payload)

    assert parsed.previous_output is None
    assert parsed.user_feedback is None

    parsed_with_regen = adapter.validate_python(
        {**base_payload, "previous_output": "旧稿", "user_feedback": "意见"},
    )

    assert parsed_with_regen.previous_output == "旧稿"
    assert parsed_with_regen.user_feedback == "意见"
