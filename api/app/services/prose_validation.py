from __future__ import annotations

import re

_LIMITED_THIRD_BLOCKERS = (
    re.compile(r"[（(]\s*(?:心想|内心OS|OS|暗想|暗自|想着)\s*[:：]"),
    re.compile(r"我(?:心想|觉得|暗自|暗想|想着)"),
    re.compile(r"我[^\n。！？]{0,16}(?:认为|以为|怀疑|猜测)"),
)


def validate_limited_third_prose(prose: str) -> list[str]:
    text = prose.strip()
    if not text:
        return ["正文为空"]

    issues: list[str] = []
    for pattern in _LIMITED_THIRD_BLOCKERS:
        if pattern.search(text):
            issues.append("检测到限制性第三人称违规表达")
            break
    return issues
