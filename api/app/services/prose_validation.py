from __future__ import annotations

import re

_LIMITED_THIRD_BLOCKERS = (
    re.compile(r"[（(]\s*(?:心想|内心OS|OS|暗想|暗自|想着)\s*[:：]"),
    re.compile(r"我(?:心想|觉得|暗自|暗想|想着)"),
    re.compile(r"我[^\n。！？]{0,16}(?:认为|以为|怀疑|猜测)"),
)

_FIRST_PERSON_NARRATION = re.compile(
    r"(?<![\w])我(?:"
    r"[^\n。！？“”‘’\"'，,；;：:、]{0,8}"
    r"(?:推开|走到|看见|看到|抬手|伸手|低头|转身|站起|坐下|"
    r"按住|握住|抓住|松开|听见|闻到|感觉|感到|意识到|知道|明白|"
    r"想起|想要|决定|盯着|望着|看着|迈出|走进|走出|走向|停下)"
    r"|[把被对向从在给将])"
)

_QUOTE_PAIRS = {
    "“": "”",
    "‘": "’",
    '"': '"',
    "'": "'",
    "《": "》",
}


def validate_limited_third_prose(prose: str) -> list[str]:
    text = prose.strip()
    if not text:
        return ["正文为空"]

    issues: list[str] = []
    for pattern in _LIMITED_THIRD_BLOCKERS:
        if pattern.search(text):
            issues.append("检测到限制性第三人称违规表达")
            break
    if not issues and _FIRST_PERSON_NARRATION.search(_strip_quoted_text(text)):
        issues.append("检测到限制性第三人称违规表达")
    return issues


def _strip_quoted_text(text: str) -> str:
    chars = list(text)
    quote_stack: list[str] = []
    for index, char in enumerate(chars):
        if quote_stack:
            chars[index] = " "
            if char == quote_stack[-1]:
                quote_stack.pop()
            continue
        closing = _QUOTE_PAIRS.get(char)
        if closing is not None:
            chars[index] = " "
            quote_stack.append(closing)
    return "".join(chars)
