from __future__ import annotations

from typing import Any, Literal

from langchain_core.messages import HumanMessage

PromptInjectionMode = Literal["analysis", "immersion", "none"]

INNER_OS_MARKER = (
    "\n\n【正文沉浸要求】在你的思考过程（<think>标签内）中，请遵守以下规则：\n"
    "1. 聚焦场景连续性、五感细节、动作链和对白潜台词，先判断下一段如何自然承接前文。\n"
    "2. 思考时只规划可外化到正文的动作、停顿、表情、语气和环境反馈，不进行角色扮演式内心戏表演。\n"
    "3. 最终输出必须服从系统提示中声明的叙事视角与输出格式，不要把思考过程或视角说明写进正文。"
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
