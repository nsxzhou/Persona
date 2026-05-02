from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError
from app.prompts.beat import (
    build_beat_generate_system_prompt,
    build_beat_generate_user_message,
)
from app.prompts.chapter_plan import (
    build_volume_chapters_system_prompt,
    build_volume_chapters_user_message,
)
from app.prompts.concept import (
    build_concept_generate_system_prompt,
    build_concept_generate_user_message,
)
from app.prompts.continuity import build_continuity_system_prompt
from app.prompts.memory_sync import (
    build_bible_update_system_prompt,
    build_bible_update_user_message,
    build_chapter_summary_system_prompt,
    build_story_summary_system_prompt,
)
from app.prompts.outline import (
    build_volume_generate_system_prompt,
    build_volume_generate_user_message,
)
from app.prompts.prose_writer import (
    build_beat_expand_system_prompt,
    build_beat_expand_user_message,
)
from app.prompts.section_router import (
    build_section_system_prompt,
    build_section_user_message,
)
from app.schemas.novel_workflows import NovelWorkflowCreateRequest
from app.schemas.prompt_profiles import GenerationProfile

def test_world_building_prompt_ties_setting_to_reader_desire_supply() -> None:
    prompt = build_section_system_prompt("world_building", length_preset="long")

    assert "世界观不是资料库，而是主角欲望和读者期待的供给系统" in prompt
    assert "设定可以是极端的阶层落差与禁忌秩序" in prompt
    assert "或者是为了让主角装逼打脸、开后宫而量身定制的无敌金手指与系统" in prompt


def test_editor_prompts_enforce_publishable_adult_tension_boundary() -> None:
    prompts = [
        build_concept_generate_system_prompt(),
        build_section_system_prompt("world_building", length_preset="long"),
        build_section_system_prompt("characters_blueprint", length_preset="long"),
        build_section_system_prompt("outline_master", length_preset="long"),
        build_section_system_prompt("outline_detail", length_preset="long"),
        build_volume_generate_system_prompt(length_preset="long"),
        build_volume_chapters_system_prompt(),
        build_beat_generate_system_prompt(),
        build_beat_expand_system_prompt(),
    ]

    for prompt in prompts:
        assert "未成年相关内容绝对禁止" in prompt
        assert "充分发挥“安全地打破禁忌”带来的背德刺激" in prompt


def test_adjacent_prompts_preserve_grounded_reading() -> None:
    characters_prompt = build_section_system_prompt("characters_blueprint", length_preset="long")
    outline_prompt = build_section_system_prompt("outline_master", length_preset="long")

    assert "沿用世界观已确定的题材解释，不得臆想毫无根据的设定" in characters_prompt
    assert "沿用世界观已确定的题材解释，不得臆想毫无根据的设定" in outline_prompt


def test_creative_planning_sections_prefer_useful_detail_over_maximal_fill() -> None:
    prompts = [
        build_section_system_prompt("world_building", length_preset="long"),
        build_section_system_prompt("characters_blueprint", length_preset="long"),
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
        "characters_blueprint",
        style_prompt="# Style Prompt\n风格约束\n",
        plot_prompt="# Plot Prompt\n情节约束\n",
        length_preset="long",
    )
    assert "# Plot Prompt\n情节约束" in characters_prompt
    assert "不得照搬样本角色、设定、事件" in characters_prompt


def test_planning_prompts_add_visible_plot_fingerprint_contract() -> None:
    prompts = [
        build_concept_generate_system_prompt(
            style_prompt="# Style Prompt\n风格约束\n",
            plot_prompt="# Plot Prompt\n核心驱动轴：信息差胁迫 → 利益绑定 → 资源兑现\n",
        ),
        build_section_system_prompt(
            "world_building",
            plot_prompt="# Plot Prompt\n核心驱动轴：信息差胁迫 → 利益绑定 → 资源兑现\n",
            length_preset="long",
        ),
        build_section_system_prompt(
            "characters_blueprint",
            plot_prompt="# Plot Prompt\n核心驱动轴：信息差胁迫 → 利益绑定 → 资源兑现\n",
            length_preset="long",
        ),
        build_section_system_prompt(
            "outline_master",
            plot_prompt="# Plot Prompt\n核心驱动轴：信息差胁迫 → 利益绑定 → 资源兑现\n",
            length_preset="long",
        ),
        build_section_system_prompt(
            "outline_detail",
            plot_prompt="# Plot Prompt\n核心驱动轴：信息差胁迫 → 利益绑定 → 资源兑现\n",
            length_preset="long",
        ),
        build_volume_generate_system_prompt(
            plot_prompt="# Plot Prompt\n核心驱动轴：信息差胁迫 → 利益绑定 → 资源兑现\n",
            length_preset="long",
        ),
        build_volume_chapters_system_prompt(
            plot_prompt="# Plot Prompt\n核心驱动轴：信息差胁迫 → 利益绑定 → 资源兑现\n",
        ),
        build_beat_generate_system_prompt(
            plot_prompt="# Plot Prompt\n核心驱动轴：信息差胁迫 → 利益绑定 → 资源兑现\n",
        ),
        build_beat_expand_system_prompt(
            plot_prompt="# Plot Prompt\n核心驱动轴：信息差胁迫 → 利益绑定 → 资源兑现\n",
        ),
    ]

    for prompt in prompts:
        assert "Plot 指纹落地契约" in prompt
        assert "核心驱动轴" in prompt
        assert "允许规划单元完全聚焦于极度的“爽感”、金手指大爆发、或是彻底的欲望/肉体征服" in prompt
        assert "输出中必须让读者看见 Plot Pack 如何改变当前项目" in prompt
        assert "不能只把 Plot Pack 当作背景参考" in prompt


def test_plot_prompt_contract_keeps_old_terms_out_of_direct_generation_targets() -> None:
    prompt = build_beat_expand_system_prompt(
        plot_prompt=(
            "# Plot Prompt\n"
            "旧模板：公共情欲压迫、密室双修、催眠控制、药物控制、未经同意越界。\n"
        )
    )

    assert "旧模板：公共情欲压迫、密室双修、催眠控制、药物控制、未经同意越界。" in prompt
    assert "遗留高风险 Plot Pack 抽象化" not in prompt


def test_concept_generate_prompt_injects_style_and_plot_profiles_before_role_prompt() -> None:
    prompt = build_concept_generate_system_prompt(
        style_prompt="# Style Prompt\n冷白、短句、压迫感\n",
        plot_prompt="# Plot Prompt\n核心驱动轴：信息差胁迫 → 利益绑定 → 资源兑现\n",
    )

    assert "# Style Prompt\n冷白、短句、压迫感" in prompt
    assert "# Plot Prompt\n核心驱动轴" in prompt
    assert prompt.index("# Style Prompt\n冷白、短句、压迫感") < prompt.index("# Plot Prompt\n核心驱动轴")
    assert prompt.index("# Plot Prompt\n核心驱动轴") < prompt.index("你是一位深耕网文市场")
    assert "概念生成阶段也必须应用已选 Plot/Style Profile" in prompt
    assert "标题和简介要体现 Plot Pack 的主驱动轴、读者追读问题和角色功能位" in prompt


def test_character_prompt_prioritizes_conflict_function_over_packaging() -> None:
    prompt = build_section_system_prompt("characters_blueprint", length_preset="long")

    assert "角色信息优先回答以下问题" in prompt
    assert "他是谁，为什么此刻会入局" in prompt
    assert "他如何卡住主角，或为什么能帮主角破局" in prompt
    assert "主角能利用、交换、规避或反制他的点是什么" in prompt
    assert "角色弧光" not in prompt
    assert "反差设计" not in prompt
    assert "阶段性反派（至少 1 个）" not in prompt


def test_character_prompt_assigns_reader_hook_functions() -> None:
    prompt = build_section_system_prompt("characters_blueprint", length_preset="long")

    assert "奖励源（如绝色红颜、可掠夺资源）、阻力源、压迫源、反转源、情绪牵引源" in prompt
    assert "角色能让读者期待主角得到什么、压过什么、推倒谁、彻底征服谁，或是提供绝对忠诚的避风港" in prompt
    assert "避免只写人设标签或空泛魅力描述" in prompt


def test_character_prompt_uses_length_budget_and_importance_tiers() -> None:
    short_prompt = build_section_system_prompt("characters_blueprint", length_preset="short")
    medium_prompt = build_section_system_prompt("characters_blueprint", length_preset="medium")
    long_prompt = build_section_system_prompt("characters_blueprint", length_preset="long")

    assert "关键角色池目标：6-9 个" in short_prompt
    assert "关键角色池目标：10-14 个" in medium_prompt
    assert "关键角色池目标：14-22 个" in long_prompt
    assert "T0：主角" in long_prompt
    assert "T1：核心关系人/核心对手" in long_prompt
    assert "T2：重要配角/阶段性阻力/奖励源" in long_prompt
    assert "T3：伏笔角色/后期引线/势力代表" in long_prompt
    assert "先满足角色池数量，再按重要程度分配详略" in long_prompt


def test_character_budget_hint_ties_each_tier_to_reader_function_and_prompt_weight() -> None:
    prompt = build_section_system_prompt("characters_blueprint", length_preset="long")

    assert "角色不是设定展示位，而是追读功能位" in prompt
    assert "T0 主角承担欲望入口、升级反馈和最终胜负" in prompt
    assert "T1 承担核心压迫、核心奖励、核心背叛或核心关系兑现" in prompt
    assert "T2 承担阶段性阻力、资源入口、情绪缓冲或小高潮触发" in prompt
    assert "T3 只保留一个可回收的钩子" in prompt
    assert "不要把 T2/T3 写成完整人物小传" in prompt


def test_outline_master_prompt_organizes_progress_around_main_pleasure_axis() -> None:
    prompt = build_section_system_prompt("outline_master", length_preset="long")

    assert "先判断这本书当前真正靠什么让人继续看下去" in prompt
    assert "围绕同一条主爽点主线组织推进" in prompt
    assert "不要为了拉大规模而额外铺地图、体系、势力层级" in prompt
    assert "以「阶段」为单位规划" in prompt
    assert "地图换挡" not in prompt
    assert "阶段 Boss/核心对手" not in prompt


def test_outline_master_prompt_requires_driver_axis_payoff_and_hook_types() -> None:
    prompt = build_section_system_prompt("outline_master", length_preset="long")

    assert "主驱动轴" in prompt
    assert "当前阶段的核心兑现物" in prompt
    assert "读者下一阶段最想看主角拿到什么、压过谁、推倒谁、彻底征服谁" in prompt
    assert "钩子类型" in prompt


def test_outline_master_prompt_requires_complete_story_closure() -> None:
    prompt = build_section_system_prompt("outline_master", length_preset="long")

    assert "必须覆盖开局局面、核心矛盾、中段升级、终局对抗、结局与余波" in prompt
    assert "必须写明终局结局/最终代价" in prompt
    assert "不能只写近期方向" in prompt


def test_outline_closure_hint_requires_payoff_chain_not_official_summary() -> None:
    prompt = build_section_system_prompt("outline_master", length_preset="long")

    assert "总纲不是世界设定摘要，而是全书追读承诺" in prompt
    assert "开局压制如何逼主角入局" in prompt
    assert "中段升级如何把金钱、武力、身份或关系转成更大筹码" in prompt
    assert "终局要写清主角最终压过谁、拿到什么、失去或付出什么" in prompt
    assert "余波要留下新的秩序、关系归属或禁忌后果" in prompt


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

    assert "章末钩子" in prompt
    assert "可以是悬念、反转、新压力、关系变化或阶段性兑现" in prompt
    assert "不必每章硬凹爆点" in prompt
    assert "章节末推动点" not in prompt
    assert "每章结尾必须有一个让读者想翻下一章的悬念或爆点" not in prompt


def test_outline_detail_prompt_uses_stable_markdown_structure() -> None:
    prompt = build_section_system_prompt("outline_detail", length_preset="short")

    assert "每个规划块用二级标题（## ）" in prompt
    assert "需要拆到章节时，再在对应规划块下使用三级标题（### ）列出章节" in prompt
    assert "不要求固定写成三幕、几卷或多少章" in prompt
    assert "短篇不设分卷，直接列出章节" not in prompt


def test_outline_detail_prompt_targets_next_chapter_reader_payoff() -> None:
    prompt = build_section_system_prompt("outline_detail", length_preset="long")

    assert "每章都要回答：下一章读者到底在等什么兑现" in prompt
    assert "拿到资源、完成打脸、扳回压制、彻底推倒、精神与肉体双重控制或阶层跃升" in prompt
    assert "悬念必须明确勾着特定的多巴胺反馈、征服欲或生理/情感期待" in prompt


def test_outline_detail_prompt_limits_detailed_chapters_to_first_or_current_volume() -> None:
    prompt = build_section_system_prompt("outline_detail", length_preset="long")

    assert "全书卷级/阶段级规划目标：8-12 个规划块" in prompt
    assert "章节详纲默认只详拆首卷或当前卷：20-40 章" in prompt
    assert "后续卷只保留主驱动轴、兑现物、核心阻力、卷尾推动点和角色状态变化" in prompt


def test_volume_budget_hint_separates_full_book_volume_promise_from_current_chapter_detail() -> None:
    prompt = build_section_system_prompt("outline_detail", length_preset="long")

    assert "卷纲负责全书追读承诺，章节详纲负责当前卷执行" in prompt
    assert "首卷/当前卷要拆到章末期待" in prompt
    assert "后续卷不要虚构完整章节目录" in prompt
    assert "每个后续卷至少交代压制来源、半兑现、反噬、新地图或新关系筹码" in prompt


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


def test_volume_generate_prompt_uses_neutral_project_wording_and_stable_structure() -> None:
    prompt = build_volume_generate_system_prompt(length_preset="medium")

    assert "正在为自己的新书规划整体结构" in prompt
    assert "每个规划块用二级标题（## ）" in prompt
    assert "不要输出顶层一级标题（# ）" in prompt
    assert "卷级字段只能用项目符号、加粗字段或引用行表达，不要使用三级标题（### ）" in prompt
    assert "只输出规划结构，不要输出任何章节内容" in prompt
    assert "不要求固定写成三幕、几卷或多少个阶段" in prompt
    assert "长篇新书" not in prompt


def test_volume_generate_prompt_requires_driver_axis_and_payoff_rhythm() -> None:
    prompt = build_volume_generate_system_prompt(length_preset="long")

    assert "每一卷都要围绕同一条主驱动轴推进" in prompt
    assert "本卷主打的兑现物" in prompt
    assert "压制后兑现、兑现后反噬" in prompt
    assert "不要把分卷写成只有地图扩大、势力变多的目录扩写" in prompt
    assert "全书卷级/阶段级规划目标：8-12 个规划块" in prompt
    assert "后续卷只保留主驱动轴、兑现物、核心阻力、卷尾推动点和角色状态变化" in prompt


def test_volume_chapters_prompt_injects_plot_prompt_after_style_prompt() -> None:
    prompt = build_volume_chapters_system_prompt(
        style_prompt="# Style Prompt\n风格约束\n",
        plot_prompt="# Plot Prompt\n情节约束\n",
    )

    assert "# Style Prompt\n风格约束" in prompt
    assert "# Plot Prompt\n情节约束" in prompt
    assert prompt.index("# Style Prompt\n风格约束") < prompt.index("# Plot Prompt\n情节约束")
    assert prompt.index("# Plot Prompt\n情节约束") < prompt.index("你是一位起点白金作家")


def test_volume_chapters_prompt_uses_current_volume_chapter_budget() -> None:
    prompt = build_volume_chapters_system_prompt(length_preset="medium")

    assert "章节详纲默认只详拆首卷或当前卷：12-25 章" in prompt
    assert "不要输出顶层一级标题（# ）" in prompt
    assert "三级标题只用于真实章节，必须写成「### 第 N 章：章名」" in prompt
    assert "只为当前卷输出章节详纲" in prompt
    assert "禁止输出 Markdown 表格" in prompt
    assert "禁止输出「第9-11章」这类范围章" in prompt
    assert "每个章节块必须同时包含「核心事件」「情绪走向」「章末钩子」" in prompt


def test_volume_generate_prompt_forbids_chapter_tables_and_ranges() -> None:
    prompt = build_volume_generate_system_prompt(length_preset="medium")

    assert "禁止输出章节细纲、章节表格、章节范围列表或「第N章」条目" in prompt
    assert "不要输出章节表格、章节范围列表或「第N章」条目" in prompt


def test_outline_detail_prompt_keeps_volume_fields_out_of_h3_headings() -> None:
    prompt = build_section_system_prompt("outline_detail", length_preset="long")

    assert "不要输出顶层一级标题（# ）" in prompt
    assert "卷级字段不要使用三级标题（### ）" in prompt
    assert "只有真实章节可使用「### 第 N 章：章名」" in prompt


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

    assert "长期 persistent 事件列表" in system_prompt
    assert "严禁像流水账一样记录每章剧情" in system_prompt
    assert "优先判断是否无需更新" in system_prompt
    assert "严禁使用“沿用旧内容”" in system_prompt


def test_bible_update_prompt_tracks_only_persistent_compliant_tension() -> None:
    system_prompt = build_bible_update_system_prompt()

    assert "只记录会持续影响后续选择的关系变化、利益交换，或金手指/系统的升级进度" in system_prompt
    assert "准确记录关系进阶的里程碑，包括情感投射的加深、身体关系的突破（如一垒、二垒、本垒打等）、控制深度的增加或堕落阶段的演进" in system_prompt
    assert "必须记录能提供“纯粹爽感”、“权力具象化”或“打破禁忌”成果的关键进展" in system_prompt


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


def test_concept_generate_prompt_requires_reader_retention_diagnosis_and_driver_variants() -> None:
    prompt = build_concept_generate_system_prompt()

    assert "读者为什么会点进来并继续追" in prompt
    assert "主驱动轴" in prompt
    assert "升级/权力扩张、局势反压、身份逆转、资源掠夺、关系张力、暧昧兑现" in prompt
    assert "不是只换标题和设定表皮" in prompt

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
    characters_prompt = build_section_system_prompt("characters_blueprint", length_preset="long")
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


def test_beat_generate_prompt_requires_actionable_reader_hooks_instead_of_only_emotion() -> None:
    prompt = build_beat_generate_system_prompt()

    assert "不要编号、不要项目符号、不要标题、不要代码块、不要前言和总结" in prompt
    assert "格式必须严格为：[情绪标签] 事件描述" in prompt
    assert "不要只写情绪变化，还要写清这一拍具体让读者追什么（如期待更深的堕落、更极致的打脸）" in prompt
    assert "压制、夺回、极致打脸、关系突破、打破禁忌、彻底征服或堕落" in prompt
    assert "最后一拍要明确勾住下一拍最想看的兑现" in prompt


def test_beat_expand_prompt_blocks_hollow_prose_and_requires_payoff_motion() -> None:
    prompt = build_beat_expand_system_prompt(
        generation_profile=GenerationProfile(
            target_market="mainstream",
            genre_mother="urban",
            desire_overlays=[],
            intensity_level="plot_only",
            pov_mode="limited_third",
            morality_axis="gray_pragmatism",
            pace_density="balanced",
        )
    )

    assert "每一段都要落下可感知的读者奖励（如极致的多巴胺爽感、金钱权力的兑现、或纯粹的生理与欲望满足）" in prompt
    assert "允许大段甚至整章的纯粹氛围、五感描写和欲望宣泄，充分满足读者的期待感与征服欲" in prompt
    assert "让读者体验主角正在享受绝对的权力掌控、彻底推倒高冷角色、或享受绝对忠诚的后宫陪伴" in prompt
    assert "视角约束" in prompt
    assert "不要写括号式内心独白" in prompt
    assert "不要直接写“我心想”" in prompt


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


def test_creative_fixed_prompts_embed_commercial_male_reader_engine() -> None:
    prompts = [
        build_concept_generate_system_prompt(),
        build_section_system_prompt("world_building", length_preset="long"),
        build_section_system_prompt("characters_blueprint", length_preset="long"),
        build_section_system_prompt("outline_master", length_preset="long"),
        build_section_system_prompt("outline_detail", length_preset="long"),
        build_volume_generate_system_prompt(length_preset="long"),
        build_volume_chapters_system_prompt(length_preset="long"),
        build_beat_generate_system_prompt(),
        build_beat_expand_system_prompt(),
    ]

    for prompt in prompts:
        assert "男频商业驱动内核" in prompt
        assert "力量与权力的扩张" in prompt
        assert "欲望满足" in prompt
        assert "压制 -> 反制 -> 兑现 -> 新压力" in prompt
        assert "升级反馈、资源掠夺、身份逆转、关系占有" in prompt
        assert "安全地打破禁忌" in prompt
        assert "读者下一章到底在等什么" in prompt


def test_maintenance_prompts_track_serial_payoff_debt_without_breaking_contracts() -> None:
    bible_prompt = build_bible_update_system_prompt()
    chapter_summary_prompt = build_chapter_summary_system_prompt()
    story_summary_prompt = build_story_summary_system_prompt()
    continuity_prompt = build_continuity_system_prompt()

    assert "追读债务" in bible_prompt
    assert "权力进度、关系里程碑、伏笔债务、兑现成果" in bible_prompt
    assert "## 角色动态状态" in bible_prompt
    assert "## 运行时状态" in bible_prompt
    assert "## 伏笔与线索追踪" in bible_prompt

    assert "只保留会改变后续局面的内容" in chapter_summary_prompt
    assert "爽点兑现、关系变化、伏笔债务" in story_summary_prompt
    assert "不是语病审稿，而是追读风险审校" in continuity_prompt
    assert "## Verdict" in continuity_prompt


def test_runtime_initialization_prompts_are_serial_state_ledgers_not_generic_docs() -> None:
    characters_status = build_section_system_prompt("characters_status")
    runtime_state = build_section_system_prompt("runtime_state")
    runtime_threads = build_section_system_prompt("runtime_threads")

    assert "连载状态账本" in characters_status
    assert "谁的欲望被撬动、谁欠了债、谁刚得到或失去筹码" in characters_status
    assert "不要写成角色百科" in characters_status

    assert "剧情总账" in runtime_state
    assert "只记录会改变后续局面的事件" in runtime_state
    assert "爽点兑现、压制来源、反噬和新压力" in runtime_state

    assert "追读债务清单" in runtime_threads
    assert "伏笔必须服务后续兑现、反转、打脸、关系突破或禁忌后果" in runtime_threads
    assert "不要罗列装饰性谜语" in runtime_threads


def test_common_runtime_prompt_rules_drop_official_assistant_tone() -> None:
    from app.prompts.common import JSON_ONLY_RULE, MARKDOWN_ONLY_RULE, NO_PREFACE_RULES

    assert "直接落正文/条目，不要写工作汇报" in MARKDOWN_ONLY_RULE
    assert "只吐 JSON 本体" in JSON_ONLY_RULE
    assert "不要写“好的”“下面是”“基于你提供的报告/摘要”“作为……我将……”" in NO_PREFACE_RULES
    assert "额外解释" not in MARKDOWN_ONLY_RULE


def test_non_analysis_fixed_prompts_do_not_keep_generic_official_sections() -> None:
    prompts = [
        build_section_system_prompt("world_building", length_preset="long"),
        build_section_system_prompt("characters_blueprint", length_preset="long"),
        build_section_system_prompt("outline_master", length_preset="long"),
        build_section_system_prompt("outline_detail", length_preset="long"),
        build_volume_generate_system_prompt(length_preset="long"),
        build_volume_chapters_system_prompt(length_preset="long"),
        build_beat_generate_system_prompt(),
        build_beat_expand_system_prompt(),
        build_bible_update_system_prompt(),
        build_chapter_summary_system_prompt(),
        build_story_summary_system_prompt(),
    ]

    banned = [
        "输出要求：",
        "当前任务是：",
        "请根据传入",
        "请基于已有上下文，生成一份",
        "你是一个专业",
        "额外解释",
    ]
    for prompt in prompts:
        for phrase in banned:
            assert phrase not in prompt


def test_user_messages_avoid_polite_assistant_request_wording() -> None:
    concept_message = build_concept_generate_user_message("灵感", 3)
    section_message = build_section_user_message(
        "world_building",
        {
            "description": "",
            "world_building": "",
            "characters_blueprint": "",
            "outline_master": "",
            "outline_detail": "",
            "runtime_state": "",
            "runtime_threads": "",
        },
    )

    assert "灵感输入，产出 3 个小说概念" in concept_message
    assert "请根据以下灵感描述生成" not in concept_message
    assert "没有其他设定，直接按当前创意开局" in section_message
    assert "请基于你的创意自由发挥" not in section_message


def test_section_generate_request_only_uses_project_context_fields() -> None:
    adapter = TypeAdapter(NovelWorkflowCreateRequest)

    from_description = adapter.validate_python({
        "intent_type": "section_generate",
        "section": "world_building",
        "project_id": "project-1",
    })
    from_inspiration_only = adapter.validate_python({
        "intent_type": "section_generate",
        "section": "world_building",
        "inspiration": "旧字段",
    })

    assert from_description.project_id == "project-1"
    assert from_inspiration_only.inspiration == "旧字段"


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
    assert "用户意见的优先级高于上一版结果" in regen_prompt
    assert "不能只改标题、标签或表层包装" in regen_prompt


def test_section_user_message_appends_previous_output_and_user_feedback() -> None:
    message = build_section_user_message(
        "world_building",
        {
            "description": "简介文本",
            "world_building": "",
            "characters_blueprint": "",
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

    assert "灵感输入，产出 3 个小说概念" in message
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
        "### 本卷核心驱动轴\n主角从被动到主动。",
        previous_output="旧章节列表",
        user_feedback="减少支线",
    )

    assert "### 当前卷原始规划" in message
    assert "主角从被动到主动。" in message
    assert "## 上一版结果\n\n旧章节列表" in message
    assert "## 用户意见（本次必须遵循）\n\n减少支线" in message
    assert "只输出标准章节块" in message


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
            "characters_blueprint": "",
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
    "base_payload",
    [
        {"intent_type": "section_generate", "section": "world_building"},
        {"intent_type": "memory_refresh", "content_to_check": "正文", "sync_scope": "chapter_full"},
        {"intent_type": "beats_generate", "text_before_cursor": "前文"},
        {
            "intent_type": "beat_expand",
            "text_before_cursor": "前文",
            "beat": "一拍",
            "beat_index": 0,
            "total_beats": 3,
        },
        {"intent_type": "volume_chapters_generate", "volume_index": 0},
        {"intent_type": "volume_generate"},
        {"intent_type": "concept_bootstrap", "inspiration": "灵感", "provider_id": "p-1"},
    ],
)
def test_request_schemas_default_regeneration_fields_to_none(
    base_payload,
) -> None:
    adapter = TypeAdapter(NovelWorkflowCreateRequest)
    parsed = adapter.validate_python(base_payload)

    assert parsed.previous_output is None
    assert parsed.feedback is None
    if base_payload["intent_type"] == "concept_bootstrap":
        assert parsed.style_profile_id is None
        assert parsed.plot_profile_id is None

    parsed_with_regen = adapter.validate_python(
        {
            **base_payload,
            "previous_output": "旧稿",
            "feedback": "意见",
            "style_profile_id": "style-1",
            "plot_profile_id": "plot-1",
        }
        if base_payload["intent_type"] == "concept_bootstrap"
        else {**base_payload, "previous_output": "旧稿", "feedback": "意见"},
    )

    assert parsed_with_regen.previous_output == "旧稿"
    assert parsed_with_regen.feedback == "意见"
    assert parsed_with_regen.model_dump(exclude_none=True)["feedback"] == "意见"
    if base_payload["intent_type"] == "concept_bootstrap":
        assert parsed_with_regen.style_profile_id == "style-1"
        assert parsed_with_regen.plot_profile_id == "plot-1"


@pytest.mark.parametrize(
    "unexpected_field",
    [
        {"user_feedback": "意见"},
        {"model": "gpt-4.1-mini"},
    ],
)
def test_request_schema_rejects_noncanonical_workflow_fields(
    unexpected_field,
) -> None:
    adapter = TypeAdapter(NovelWorkflowCreateRequest)

    with pytest.raises(ValidationError):
        adapter.validate_python(
            {
                "intent_type": "concept_bootstrap",
                "inspiration": "灵感",
                "provider_id": "p-1",
                **unexpected_field,
            },
        )
