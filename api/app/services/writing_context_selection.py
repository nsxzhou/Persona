from __future__ import annotations

import re
from dataclasses import dataclass


MAX_ACTIVE_CHARACTERS = 8
FALLBACK_CHARACTER_CARDS = 6
MAX_CHARACTER_CARD_CHARS = 1400
CHARACTERS_BLUEPRINT_BUDGET = 9000
CHARACTERS_STATUS_BUDGET = 7000

STORY_SUMMARY_BUDGET = 4000
WORLD_BUILDING_BUDGET = 4000
OUTLINE_MASTER_BUDGET = 3000
OUTLINE_DETAIL_BUDGET = 7000
RUNTIME_STATE_BUDGET = 5000
RUNTIME_THREADS_BUDGET = 4000

_CARD_HEADING_RE = re.compile(r"(?m)^(?P<marker>#{2,3})\s+(?P<title>.+?)\s*$")
_TRUNCATED_MARKER = "\n\n（已按上下文预算截断）"


@dataclass(frozen=True)
class CharacterCard:
    title: str
    body: str

    @property
    def markdown(self) -> str:
        return self.body.strip()


@dataclass(frozen=True)
class SelectedWritingContext:
    description: str = ""
    world_building: str = ""
    characters_blueprint: str = ""
    outline_master: str = ""
    outline_detail: str = ""
    characters_status: str = ""
    runtime_state: str = ""
    runtime_threads: str = ""
    story_summary: str = ""
    active_character_focus: str = ""

    def as_bible(self) -> dict[str, str]:
        return {
            "world_building": self.world_building,
            "characters_blueprint": self.characters_blueprint,
            "outline_master": self.outline_master,
            "outline_detail": self.outline_detail,
            "characters_status": self.characters_status,
            "runtime_state": self.runtime_state,
            "runtime_threads": self.runtime_threads,
            "story_summary": self.story_summary,
            "active_character_focus": self.active_character_focus,
        }


def select_writing_context(
    *,
    current_bible: dict[str, str],
    active_character_names: list[str],
    current_chapter_context: str,
    text_before_cursor: str,
    description: str = "",
) -> SelectedWritingContext:
    blueprint = _select_character_section(
        current_bible.get("characters_blueprint", ""),
        active_character_names=active_character_names,
        search_text=f"{current_chapter_context}\n{text_before_cursor}",
        total_budget=CHARACTERS_BLUEPRINT_BUDGET,
    )
    status = _select_character_section(
        current_bible.get("characters_status", ""),
        active_character_names=active_character_names,
        search_text=f"{current_chapter_context}\n{text_before_cursor}",
        total_budget=CHARACTERS_STATUS_BUDGET,
    )
    active_character_focus = _build_active_character_focus(blueprint, status)
    return SelectedWritingContext(
        description=description,
        world_building=_limit_text(
            current_bible.get("world_building", ""),
            WORLD_BUILDING_BUDGET,
        ),
        characters_blueprint=blueprint,
        outline_master=_limit_text(
            current_bible.get("outline_master", ""),
            OUTLINE_MASTER_BUDGET,
        ),
        outline_detail=_limit_text(
            current_bible.get("outline_detail", ""),
            OUTLINE_DETAIL_BUDGET,
        ),
        characters_status=status,
        runtime_state=_limit_text(
            current_bible.get("runtime_state", ""),
            RUNTIME_STATE_BUDGET,
        ),
        runtime_threads=_limit_text(
            current_bible.get("runtime_threads", ""),
            RUNTIME_THREADS_BUDGET,
        ),
        story_summary=_limit_text(
            current_bible.get("story_summary", ""),
            STORY_SUMMARY_BUDGET,
        ),
        active_character_focus=active_character_focus,
    )


def _select_character_section(
    markdown: str,
    *,
    active_character_names: list[str],
    search_text: str,
    total_budget: int,
) -> str:
    cards = _split_character_cards(markdown)
    if not cards:
        return _limit_text(markdown, total_budget)

    active_names = _normalize_names(active_character_names)
    selected_indexes = [
        index
        for index, card in enumerate(cards)
        if _card_matches(card, active_names)
    ][:MAX_ACTIVE_CHARACTERS]
    if not selected_indexes:
        selected_indexes = [
            index
            for index, card in enumerate(cards)
            if card.title and card.title in search_text
        ][:MAX_ACTIVE_CHARACTERS]
    if not selected_indexes:
        selected_indexes = list(range(min(FALLBACK_CHARACTER_CARDS, len(cards))))

    selected_set = set(selected_indexes)
    selected_parts = [
        _limit_character_card(cards[index].markdown)
        for index in selected_indexes
    ]
    omitted_titles = [
        card.title for index, card in enumerate(cards) if index not in selected_set
    ]
    if omitted_titles:
        selected_parts.append(
            "## 非活跃角色索引\n\n"
            + "\n".join(f"- {title}" for title in omitted_titles if title)
        )
    return _limit_text("\n\n".join(part for part in selected_parts if part), total_budget)


def _split_character_cards(markdown: str) -> list[CharacterCard]:
    matches = list(_CARD_HEADING_RE.finditer(markdown))
    if not matches:
        return []
    cards: list[CharacterCard] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        body = markdown[start:end].strip()
        cards.append(CharacterCard(title=match.group("title").strip(), body=body))
    return cards


def _normalize_names(names: list[str]) -> list[str]:
    normalized: list[str] = []
    for name in names:
        stripped = str(name).strip()
        if stripped and stripped not in normalized:
            normalized.append(stripped)
    return normalized[:MAX_ACTIVE_CHARACTERS]


def _card_matches(card: CharacterCard, names: list[str]) -> bool:
    if not names:
        return False
    haystack = f"{card.title}\n{card.body}"
    return any(name in haystack for name in names)


def _limit_character_card(markdown: str) -> str:
    return _limit_text(markdown, MAX_CHARACTER_CARD_CHARS)


def _limit_text(text: str, max_chars: int) -> str:
    stripped = (text or "").strip()
    if len(stripped) <= max_chars:
        return stripped
    body_budget = max(max_chars - len(_TRUNCATED_MARKER), 0)
    return stripped[:body_budget].rstrip() + _TRUNCATED_MARKER


def _build_active_character_focus(blueprint: str, status: str) -> str:
    parts: list[str] = []
    if blueprint.strip():
        parts.append("## 活跃角色基础设定\n\n" + blueprint.strip())
    if status.strip():
        parts.append("## 活跃角色动态状态\n\n" + status.strip())
    return "\n\n---\n\n".join(parts)
