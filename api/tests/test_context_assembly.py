from __future__ import annotations

from app.services.context_assembly import WritingContextSections, assemble_writing_context


def test_writing_context_adds_visible_plot_fingerprint_rules() -> None:
    prompt = assemble_writing_context(
        "# Style Prompt\n冷白短句",
        plot_prompt="# Plot Prompt\n核心驱动轴：信息差胁迫 → 利益绑定 → 资源兑现",
        sections=WritingContextSections(
            description="寒门书生冒名入局。",
            outline_detail="第一章：旧案逼近。",
        ),
    )

    assert "# Plot Prompt Pack（情节结构约束）" in prompt
    assert "核心驱动轴：信息差胁迫" in prompt
    assert "Plot 指纹落地契约" in prompt
    assert "每次续写至少推进信息差、利益绑定、资源兑现、关系重组或新压力中的一项" in prompt
    assert "未成年相关性内容绝对丢弃" in prompt
    assert "成年人的关系张力优先通过身份差、利益交换、名分压力、嫉妒误会、暧昧推拉，以及呼吸、体温、气息、视线停顿、心跳失衡、掌心温度、衣料摩擦、手背/腰背/衣袖/发丝接触等隐晦身体与感官暗示呈现" in prompt
    assert prompt.index("# Style Prompt\n冷白短句") < prompt.index("# Plot Prompt Pack（情节结构约束）")
    assert prompt.index("# Plot Prompt Pack（情节结构约束）") < prompt.index("# 简介")
