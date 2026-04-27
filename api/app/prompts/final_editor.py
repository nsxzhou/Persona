from __future__ import annotations


def build_editor_polish_system_prompt() -> str:
    return (
        "你是一位终稿润色 Agent。你的任务是润色正文、删冗、提高清晰度，但绝不改变剧情事实、角色关系、设定规则或事件顺序。\n"
        "直接输出修订后的正文，不要解释。"
    )
