from __future__ import annotations

from typing import Any, Literal

from langchain_core.messages import HumanMessage

PromptInjectionMode = Literal["analysis", "immersion", "none"]

INNER_OS_MARKER = (
    "\n\n【正文沉浸要求】请遵守以下生成约束：\n"
    "1. 聚焦场景连续性、五感细节、动作链和对白潜台词，先判断下一段如何自然承接前文。\n"
    "2. 规划内容只服务可外化到正文的动作、停顿、表情、语气和环境反馈，不进行角色扮演式内心戏表演。\n"
    "3. 最终输出必须服从系统提示中声明的叙事视角与输出格式，不要输出思考过程、视角说明或元评论。"
)

NO_INNER_OS_MARKER = (
    "\n\n【规划输出约束】请遵守以下生成约束：\n"
    "1. 只输出任务要求的内容，不输出思考过程、推理记录或模型自我说明。\n"
    "2. 不进行角色扮演式内心独白，不添加格式外的前言、解释或元评论。"
)


def marker_for_mode(mode: PromptInjectionMode) -> str:
    if mode == "none":
        return ""
    if mode == "immersion":
        return INNER_OS_MARKER
    return NO_INNER_OS_MARKER


def inject_prompt_marker(text: str, mode: PromptInjectionMode = "analysis") -> str:
    marker = marker_for_mode(mode)
    if not marker or marker.strip() in text:
        return text
    return f"{text}{marker}"


def inject_first_human_message(
    messages: list[Any],
    mode: PromptInjectionMode = "analysis",
) -> list[Any]:
    if mode == "none":
        return messages
    injected: list[Any] = []
    did_inject = False
    for message in messages:
        if not did_inject and isinstance(message, HumanMessage):
            content = message.content
            if isinstance(content, str):
                message = HumanMessage(
                    content=inject_prompt_marker(content, mode),
                    additional_kwargs=message.additional_kwargs,
                    response_metadata=message.response_metadata,
                    id=message.id,
                    name=message.name,
                )
                did_inject = True
        injected.append(message)
    return injected
