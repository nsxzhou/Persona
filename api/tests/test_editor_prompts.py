from __future__ import annotations

import pytest
from pydantic import TypeAdapter
from app.services.editor_prompts import (
    build_beat_expand_system_prompt,
    build_beat_generate_system_prompt,
    build_bible_update_system_prompt,
    build_bible_update_user_message,
    build_concept_generate_system_prompt,
    build_section_system_prompt,
    build_section_user_message,
    build_volume_chapters_system_prompt,
    build_volume_generate_system_prompt,
)
from app.schemas.editor import SectionGenerateRequest


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


def test_adjacent_prompts_preserve_grounded_reading() -> None:
    characters_prompt = build_section_system_prompt("characters", length_preset="long")
    outline_prompt = build_section_system_prompt("outline_master", length_preset="long")

    assert "沿用世界观已确定的题材解释，不得把现实权谋误写为超自然机制或秘密体系" in characters_prompt
    assert "沿用世界观已确定的题材解释，不得把现实权谋误写为超自然机制或秘密体系" in outline_prompt


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


def test_concept_generate_prompt_requires_several_hundred_character_synopsis() -> None:
    prompt = build_concept_generate_system_prompt()

    assert "每个概念包含标题和一段可直接用作项目简介的长简介" in prompt
    assert "字数控制在 250-400 字左右" in prompt
    assert "按 2-4 个自然段组织" in prompt
    assert "不写成一句话梗概" in prompt


def test_concept_generate_prompt_uses_shared_story_spine_strategy() -> None:
    prompt = build_concept_generate_system_prompt()

    assert "共享同一故事主轴" in prompt
    assert "不能写成三本完全不同的小说" in prompt
    assert "每张卡至少拉开 2 个维度" in prompt


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


def test_section_generate_request_accepts_description_and_legacy_inspiration_alias() -> None:
    adapter = TypeAdapter(SectionGenerateRequest)

    from_description = adapter.validate_python({
        "section": "world_building",
        "description": "新的简介",
    })
    from_legacy = adapter.validate_python({
        "section": "world_building",
        "inspiration": "旧字段",
    })

    assert from_description.description == "新的简介"
    assert from_legacy.description == "旧字段"
