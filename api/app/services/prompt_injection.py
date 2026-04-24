from __future__ import annotations

from typing import Any, Literal

from langchain_core.messages import HumanMessage

PromptInjectionMode = Literal["analysis", "immersion", "none"]

INNER_OS_MARKER = (
    "\n\n【角色沉浸要求】在你的思考过程（<think>标签内）中，请遵守以下规则：\n"
    "1. 请以角色第一人称进行内心独白，用括号包裹内心活动，例如\"（心想：……）\"或\"(内心OS：……)\"\n"
    "2. 用第一人称描写角色的内心感受，例如\"我心想\"\"我觉得\"\"我暗自\"等\n"
    "3. 思考内容应沉浸在角色中，通过内心独白分析剧情和规划回复"
)

NO_INNER_OS_MARKER = (
    "\n\n【思维模式要求】在你的思考过程（<think>标签内）中，请遵守以下规则：\n"
    "1. 禁止使用圆括号包裹内心独白，例如\"（心想：……）\"或\"(内心OS：……)\"，所有分析内容直接陈述即可\n"
    "2. 禁止以角色第一人称描写内心活动，例如\"我心想\"\"我觉得\"\"我暗自\"等，请用分析性语言替代\n"
    "3. 思考内容应聚焦于剧情走向分析和回复内容规划，不要在思考中进行角色扮演式的内心戏表演"
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
