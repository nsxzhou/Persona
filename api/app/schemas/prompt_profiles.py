from __future__ import annotations

from typing import Literal
import re

from pydantic import BaseModel, Field


TargetMarket = Literal["mainstream", "nsfw"]
GenreMother = Literal["xianxia", "urban", "historical_power", "infinite_flow", "gaming"]
IntensityLevel = Literal["plot_only", "edge", "explicit", "graphic", "fetish_extreme"]
DesireOverlay = Literal[
    "harem_collect",
    "wife_steal",
    "reverse_ntr",
    "hypnosis_control",
    "corruption_fall",
    "dominance_capture",
]
PovMode = Literal["limited_third", "first_person", "deep_first"]
MoralityAxis = Literal["ruthless_growth", "gray_pragmatism", "domination_first", "vengeful"]
PaceDensity = Literal["slow", "balanced", "fast"]
ChapterGoal = Literal["advance", "payoff", "counterattack", "harvest", "seduce", "corrupt"]
PayoffTarget = Literal["power", "status", "relationship", "body", "secret", "control"]
AdultExpressionMode = IntensityLevel
HookType = Literal[
    "pressure_escalation",
    "half_payoff_then_backlash",
    "capture_then_twist",
    "seduction_then_reversal",
]


class VoiceProfile(BaseModel):
    common_expressions: str = Field(min_length=1)
    sentence_patterns: str = Field(min_length=1)
    lexical_preferences: str = Field(min_length=1)
    sentence_construction: str = Field(min_length=1)
    personal_scene_clues: str = Field(min_length=1)
    domain_regional_lexicon: str = Field(min_length=1)
    natural_irregularities: str = Field(min_length=1)
    avoided_patterns: str = Field(min_length=1)
    metaphors_imagery: str = Field(min_length=1)
    logic_and_emotion: str = Field(min_length=1)
    dialogue_modes: str = Field(min_length=1)
    values_motifs: str = Field(min_length=1)


class StoryEngineProfile(BaseModel):
    genre_mother: GenreMother
    drive_axes: list[str] = Field(min_length=1)
    payoff_objects: list[str] = Field(min_length=1)
    pressure_formulas: list[str] = Field(min_length=1)
    relation_roles: list[str] = Field(min_length=1)
    scene_verbs: list[str] = Field(min_length=1)
    hook_recipes: list[str] = Field(min_length=1)
    anti_drift_guardrails: list[str] = Field(min_length=1)


class PlotWritingGuideProfile(BaseModel):
    core_plot_formula: list[str] = Field(min_length=1)
    chapter_progression_loop: list[str] = Field(min_length=1)
    scene_construction_rules: list[str] = Field(min_length=1)
    setup_and_payoff_rules: list[str] = Field(min_length=1)
    payoff_and_tension_rhythm: list[str] = Field(min_length=1)
    side_plot_usage: list[str] = Field(min_length=1)
    hook_recipes: list[str] = Field(min_length=1)
    anti_drift_rules: list[str] = Field(min_length=1)


class IntensityProfile(BaseModel):
    intensity_level: IntensityLevel
    desire_overlays: list[DesireOverlay] = Field(default_factory=list)
    expression_focus: list[str] = Field(min_length=1)
    boundary_rules: list[str] = Field(min_length=1)
    soft_conflicts: list[str] = Field(default_factory=list)


class GenerationProfile(BaseModel):
    target_market: TargetMarket = "mainstream"
    genre_mother: GenreMother
    desire_overlays: list[DesireOverlay] = Field(default_factory=list)
    intensity_level: IntensityLevel
    pov_mode: PovMode
    morality_axis: MoralityAxis
    pace_density: PaceDensity


class ChapterObjectiveCard(BaseModel):
    chapter_goal: ChapterGoal
    payoff_target: PayoffTarget
    pressure_source: str = Field(min_length=1)
    relationship_delta: str = Field(min_length=1)
    adult_expression_mode: AdultExpressionMode
    hook_type: HookType


_LEGACY_SECTION_RE = re.compile(
    r"^##\s+(?P<name>[a-zA-Z0-9_]+)\s*$\n(?P<body>.*?)(?=^##\s+[a-zA-Z0-9_]+\s*$|\Z)",
    flags=re.MULTILINE | re.DOTALL,
)
_TITLE_SECTION_RE = re.compile(
    r"^##\s+(?P<title>[A-Za-z][A-Za-z0-9 &-]+?)\s*$\n(?P<body>.*?)(?=^##\s+[A-Za-z][A-Za-z0-9 &-]+?\s*$|\Z)",
    flags=re.MULTILINE | re.DOTALL,
)
_NUMBERED_SECTION_RE = re.compile(
    r"^##\s+(?P<number>3\.(?:[1-9]|1[0-2]))\s+(?P<title>.+?)\s*$\n(?P<body>.*?)(?=^##\s+3\.(?:[1-9]|1[0-2])\s+.+?$|\Z)",
    flags=re.MULTILINE | re.DOTALL,
)

_VOICE_SECTION_KEYS: dict[str, str] = {
    "3.1": "common_expressions",
    "3.2": "sentence_patterns",
    "3.3": "lexical_preferences",
    "3.4": "sentence_construction",
    "3.5": "personal_scene_clues",
    "3.6": "domain_regional_lexicon",
    "3.7": "natural_irregularities",
    "3.8": "avoided_patterns",
    "3.9": "metaphors_imagery",
    "3.10": "logic_and_emotion",
    "3.11": "dialogue_modes",
    "3.12": "values_motifs",
}

_VOICE_DEFAULTS: dict[str, str] = {
    "common_expressions": "当前样本中证据有限。",
    "sentence_patterns": "当前样本中证据有限。",
    "lexical_preferences": "当前样本中证据有限。",
    "sentence_construction": "当前样本中证据有限。",
    "personal_scene_clues": "当前样本中证据有限。",
    "domain_regional_lexicon": "当前样本中证据有限。",
    "natural_irregularities": "当前样本中证据有限。",
    "avoided_patterns": "当前样本中证据有限。",
    "metaphors_imagery": "当前样本中证据有限。",
    "logic_and_emotion": "当前样本中证据有限。",
    "dialogue_modes": "当前样本中证据有限。",
    "values_motifs": "当前样本中证据有限。",
}


def _extract_sections(markdown: str) -> dict[str, str]:
    return {match.group("name"): match.group("body").strip() for match in _LEGACY_SECTION_RE.finditer(markdown)}


def _section_key(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")


def _extract_title_sections(markdown: str) -> dict[str, str]:
    return {
        _section_key(match.group("title")): match.group("body").strip()
        for match in _TITLE_SECTION_RE.finditer(markdown)
    }


def _extract_numbered_sections(markdown: str) -> dict[str, str]:
    return {
        match.group("number"): match.group("body").strip()
        for match in _NUMBERED_SECTION_RE.finditer(markdown)
    }


def _flatten_section(body: str) -> str:
    return " ".join(line.strip() for line in body.splitlines() if line.strip())


def _extract_bullets(body: str) -> list[str]:
    bullets = [line[1:].strip() for line in body.splitlines() if line.lstrip().startswith("-")]
    return [line for line in bullets if line]


def derive_voice_profile(markdown: str | None) -> VoiceProfile:
    text = (markdown or "").strip()
    numbered_sections = _extract_numbered_sections(text)
    values = dict(_VOICE_DEFAULTS)
    for section_number, key in _VOICE_SECTION_KEYS.items():
        flattened = _flatten_section(numbered_sections.get(section_number, ""))
        if flattened:
            values[key] = flattened
    return VoiceProfile(**values)


def _detect_genre_mother(markdown: str) -> GenreMother:
    lowered = markdown.lower()
    if "urban" in lowered or "都市" in markdown:
        return "urban"
    if "historical_power" in lowered or "历史" in markdown or "争霸" in markdown:
        return "historical_power"
    if "infinite_flow" in lowered or "无限" in markdown or "副本" in markdown:
        return "infinite_flow"
    if "gaming" in lowered or "电竞" in markdown or "网游" in markdown:
        return "gaming"
    return "xianxia"


def derive_story_engine_profile(markdown: str | None) -> StoryEngineProfile:
    text = (markdown or "").strip()
    sections = _extract_sections(text)
    genre_body = sections.get("genre_mother", "")
    genre_mother = _extract_bullets(genre_body)[0] if _extract_bullets(genre_body) else _detect_genre_mother(text)
    return StoryEngineProfile(
        genre_mother=genre_mother,  # type: ignore[arg-type]
        drive_axes=_extract_bullets(sections.get("drive_axes", "")) or ["升级", "掠夺"],
        payoff_objects=_extract_bullets(sections.get("payoff_objects", "")) or ["力量", "资源", "关系"],
        pressure_formulas=_extract_bullets(sections.get("pressure_formulas", "")) or ["压制 -> 试探 -> 兑现 -> 反噬"],
        relation_roles=_extract_bullets(sections.get("relation_roles", "")) or ["奖励源", "阻力源", "压迫源"],
        scene_verbs=_extract_bullets(sections.get("scene_verbs", "")) or ["入局", "压制", "试探", "收割"],
        hook_recipes=_extract_bullets(sections.get("hook_recipes", "")) or ["半兑现后追加新压力"],
        anti_drift_guardrails=_extract_bullets(sections.get("anti_drift_guardrails", "")) or ["不要退化成纯气氛描写"],
    )


def derive_plot_writing_guide_profile(markdown: str | None) -> PlotWritingGuideProfile:
    text = (markdown or "").strip()
    sections = _extract_title_sections(text)

    def bullets(key: str, fallback: str) -> list[str]:
        return _extract_bullets(sections.get(key, "")) or [fallback]

    return PlotWritingGuideProfile(
        core_plot_formula=bullets("core_plot_formula", "用明确压力迫使主角做出行动选择。"),
        chapter_progression_loop=bullets(
            "chapter_progression_loop",
            "目标 -> 阻碍 -> 行动 -> 小兑现 -> 新压力。",
        ),
        scene_construction_rules=bullets("scene_construction_rules", "每个场景必须改变局面。"),
        setup_and_payoff_rules=bullets("setup_and_payoff_rules", "伏笔必须在行动或反转中兑现。"),
        payoff_and_tension_rhythm=bullets("payoff_and_tension_rhythm", "阶段性兑现后追加更大压力。"),
        side_plot_usage=bullets("side_plot_usage", "支线必须映照并回流主线。"),
        hook_recipes=bullets("hook_recipes", "章末用新威胁、新代价或新选择制造追读。"),
        anti_drift_rules=bullets("anti_drift_rules", "不要复述样本剧情或输出空泛分析。"),
    )


def extract_suggested_overlays(markdown: str | None) -> list[DesireOverlay]:
    text = (markdown or "").strip()
    sections = _extract_sections(text)
    allowed = {
        "harem_collect",
        "wife_steal",
        "reverse_ntr",
        "hypnosis_control",
        "corruption_fall",
        "dominance_capture",
    }
    overlays: list[DesireOverlay] = []
    for candidate in _extract_bullets(sections.get("suggested_overlays", "")):
        if candidate in allowed:
            overlays.append(candidate)  # type: ignore[arg-type]
    return overlays


def default_generation_profile(
    story_engine_profile: StoryEngineProfile | None = None,
    target_market: TargetMarket = "mainstream",
) -> GenerationProfile:
    genre_mother: GenreMother = "xianxia"
    if story_engine_profile is not None:
        genre_mother = story_engine_profile.genre_mother
    return GenerationProfile(
        target_market=target_market,
        genre_mother=genre_mother,
        desire_overlays=[],
        intensity_level="plot_only",
        pov_mode="limited_third",
        morality_axis="gray_pragmatism",
        pace_density="balanced",
    )


def build_intensity_profile(generation_profile: GenerationProfile) -> IntensityProfile:
    focus_by_level: dict[IntensityLevel, list[str]] = {
        "plot_only": ["剧情推进", "权力变化", "关系张力"],
        "edge": ["暧昧推拉", "身体距离", "占有欲"],
        "explicit": ["占有欲", "边界试探", "身体感官"],
        "graphic": ["支配感", "堕落过程", "身体感官"],
        "fetish_extreme": ["控制欲", "堕落过程", "极端关系偏转"],
    }
    conflicts: list[str] = []
    if generation_profile.intensity_level == "plot_only" and generation_profile.desire_overlays:
        conflicts.append("overlay 已启用，但当前强度档位仍要求以剧情推进优先。")
    return IntensityProfile(
        intensity_level=generation_profile.intensity_level,
        desire_overlays=generation_profile.desire_overlays,
        expression_focus=focus_by_level[generation_profile.intensity_level],
        boundary_rules=["未成年相关绝对移除", "强度只改变欲望落地方式，不改变主线推进义务"],
        soft_conflicts=conflicts,
    )


def build_chapter_objective_card(
    generation_profile: GenerationProfile,
    *,
    current_chapter_context: str = "",
    outline_detail: str = "",
) -> ChapterObjectiveCard:
    overlays = set(generation_profile.desire_overlays)
    chapter_goal: ChapterGoal = "advance"
    payoff_target: PayoffTarget = "power"
    relationship_delta = "推进当前局面并制造下一轮压力。"
    hook_type: HookType = "pressure_escalation"

    if overlays:
        chapter_goal = "seduce" if generation_profile.intensity_level in {"edge", "explicit"} else "corrupt"
        payoff_target = "relationship" if "harem_collect" in overlays or "wife_steal" in overlays else "control"
        relationship_delta = "从试探推进到默认暧昧绑定或支配失衡。"
        hook_type = "half_payoff_then_backlash"
    elif generation_profile.genre_mother in {"urban", "historical_power"}:
        payoff_target = "status"

    pressure_source = (current_chapter_context or outline_detail or "当前局势与主要对手施加的压力").strip()
    return ChapterObjectiveCard(
        chapter_goal=chapter_goal,
        payoff_target=payoff_target,
        pressure_source=pressure_source[:160],
        relationship_delta=relationship_delta,
        adult_expression_mode=generation_profile.intensity_level,
        hook_type=hook_type,
    )
