from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from app.schemas.projects import (
    PromptAssetInitSuggestionsResponse,
    ProjectPromptAssetResponse,
    ProjectPromptAssetSuggestionChange,
)

_PROMPT_ASSET_INIT_SYSTEM = (
    "你是小说项目的 Prompt 资产初始化编辑。你的任务是根据项目简介、Project Bible 和"
    "当前已有 Prompt 资产，提出可执行的 Prompt 资产变更建议。\n\n"
    "【硬性规则】\n"
    "1. 只输出 JSON，不要输出 Markdown、解释、代码块或额外文字。\n"
    "2. 输出必须是对象：{\"changes\": [...]}。\n"
    "3. changes 中每个对象的 action 只能是 \"new\"、\"update\"、\"disable\"。\n"
    "4. new 必须提供 payload，不能提供 asset_id。\n"
    "5. update 必须提供 asset_id 和 payload。\n"
    "6. disable 必须提供 asset_id，payload 可以省略。\n"
    "7. payload.kind 只能是 character_card、lorebook_entry、author_note。\n"
    "8. payload.scope 默认 project；只有明确绑定章节时才用 chapter。\n"
    "9. payload.title 必须简短明确，content 必须可直接放入 Prompt 栈。\n"
    "10. keywords 用于激活世界书或角色卡；author_note 可以 always_on=true 且 keywords=[]。\n"
    "11. 不要覆盖或复述 Style/Plot Profile；不要生成章节正文。\n"
    "12. 如果已有资产已经覆盖某项信息，优先 update 而不是 new；过期或重复资产用 disable。"
)


def build_prompt_asset_init_system_prompt() -> str:
    return _PROMPT_ASSET_INIT_SYSTEM


def build_prompt_asset_init_user_message(
    *,
    project_name: str,
    project_description: str,
    current_bible: dict[str, str],
    existing_assets: list[ProjectPromptAssetResponse],
) -> str:
    payload = {
        "project": {
            "name": project_name,
            "description": project_description,
        },
        "project_bible": {
            "world_building": current_bible.get("world_building", ""),
            "characters_blueprint": current_bible.get("characters_blueprint", ""),
            "outline_master": current_bible.get("outline_master", ""),
            "outline_detail": current_bible.get("outline_detail", ""),
            "characters_status": current_bible.get("characters_status", ""),
            "runtime_state": current_bible.get("runtime_state", ""),
            "runtime_threads": current_bible.get("runtime_threads", ""),
            "story_summary": current_bible.get("story_summary", ""),
        },
        "existing_prompt_assets": [
            asset.model_dump(mode="json") for asset in existing_assets
        ],
        "expected_output_schema": {
            "changes": [
                {
                    "action": "new | update | disable",
                    "asset_id": "existing asset id for update/disable, omitted for new",
                    "rationale": "short reason",
                    "payload": {
                        "kind": "character_card | lorebook_entry | author_note",
                        "scope": "project",
                        "chapter_id": None,
                        "title": "short title",
                        "content": "prompt asset content",
                        "keywords": ["activation keyword"],
                        "enabled": True,
                        "always_on": False,
                        "priority": 0,
                    },
                }
            ]
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def parse_prompt_asset_init_response(raw: str) -> PromptAssetInitSuggestionsResponse:
    text = _strip_json_fence(raw)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = _parse_legacy_markdown_suggestions(raw)
    try:
        return PromptAssetInitSuggestionsResponse.model_validate(data)
    except ValidationError as exc:
        raise ValueError("Prompt asset init output did not match suggestion schema") from exc


def render_prompt_asset_suggestions_markdown(
    suggestions: PromptAssetInitSuggestionsResponse,
) -> str:
    return json.dumps(suggestions.model_dump(mode="json"), ensure_ascii=False, indent=2)


def _strip_json_fence(markdown: str) -> str:
    stripped = markdown.strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.DOTALL)
    if match:
        return match.group(1).strip()
    return stripped


def _parse_legacy_markdown_suggestions(raw: str) -> dict[str, Any]:
    changes: list[ProjectPromptAssetSuggestionChange] = []
    current: dict[str, Any] | None = None
    body: list[str] = []

    def flush() -> None:
        nonlocal current, body
        if current is None:
            return
        payload = current.get("payload")
        if isinstance(payload, dict) and body:
            payload["content"] = "\n".join(body).strip()
        changes.append(ProjectPromptAssetSuggestionChange.model_validate(current))
        current = None
        body = []

    for line in raw.splitlines():
        stripped = line.strip()
        match = re.match(r"^##\s+(new|update|disable)\s*:?\s*(.*)$", stripped, flags=re.I)
        if match:
            flush()
            action = match.group(1).lower()
            title = match.group(2).strip() or action
            current = {"action": action, "rationale": ""}
            if action == "new":
                current["payload"] = {
                    "kind": "lorebook_entry",
                    "scope": "project",
                    "chapter_id": None,
                    "title": title,
                    "content": "",
                    "keywords": [],
                    "enabled": True,
                    "always_on": False,
                    "priority": 0,
                }
            continue
        if current is None:
            continue
        if stripped.startswith("asset_id:"):
            current["asset_id"] = stripped.split(":", 1)[1].strip() or None
            continue
        if stripped.startswith("kind:") and isinstance(current.get("payload"), dict):
            current["payload"]["kind"] = stripped.split(":", 1)[1].strip()
            continue
        if stripped.startswith("keywords:") and isinstance(current.get("payload"), dict):
            value = stripped.split(":", 1)[1]
            current["payload"]["keywords"] = [
                item.strip() for item in re.split(r"[,，]", value) if item.strip()
            ]
            continue
        if stripped.startswith("rationale:"):
            current["rationale"] = stripped.split(":", 1)[1].strip()
            continue
        if stripped:
            body.append(line)
    flush()
    return {"changes": [change.model_dump(mode="json") for change in changes]}
