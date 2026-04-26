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
    sentence_rhythm: str = Field(min_length=1)
    narrative_distance: str = Field(min_length=1)
    detail_anchors: list[str] = Field(min_length=1)
    dialogue_aggression: str = Field(min_length=1)
    irregularity_budget: str = Field(min_length=1)
    anti_ai_guardrails: list[str] = Field(min_length=1)


class StoryEngineProfile(BaseModel):
    genre_mother: GenreMother
    drive_axes: list[str] = Field(min_length=1)
    payoff_objects: list[str] = Field(min_length=1)
    pressure_formulas: list[str] = Field(min_length=1)
    relation_roles: list[str] = Field(min_length=1)
    scene_verbs: list[str] = Field(min_length=1)
    hook_recipes: list[str] = Field(min_length=1)
    anti_drift_guardrails: list[str] = Field(min_length=1)


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


_SECTION_RE = re.compile(
    r"^##\s+(?P<name>[a-zA-Z0-9_]+)\s*$\n(?P<body>.*?)(?=^##\s+[a-zA-Z0-9_]+\s*$|\Z)",
    flags=re.MULTILINE | re.DOTALL,
)


def _extract_sections(markdown: str) -> dict[str, str]:
    return {match.group("name"): match.group("body").strip() for match in _SECTION_RE.finditer(markdown)}


def _extract_bullets(body: str) -> list[str]:
    bullets = [line[1:].strip() for line in body.splitlines() if line.lstrip().startswith("-")]
    return [line for line in bullets if line]


def derive_voice_profile(markdown: str | None) -> VoiceProfile:
    text = (markdown or "").strip()
    sections = _extract_sections(text)
    detail_anchors = _extract_bullets(sections.get("detail_anchors", ""))
    anti_ai_guardrails = _extract_bullets(sections.get("anti_ai_guardrails", ""))
    return VoiceProfile(
        sentence_rhythm=(sections.get("sentence_rhythm") or "短句推进，长句用于压顶。").replace("\n", " ").strip(),
        narrative_distance=(sections.get("narrative_distance") or "贴近主角即时感官与判断。").replace("\n", " ").strip(),
        detail_anchors=detail_anchors or ["呼吸", "视线", "掌心温度"],
        dialogue_aggression=(sections.get("dialogue_aggression") or "对白偏试探、抢拍、压迫。").replace("\n", " ").strip(),
        irregularity_budget=(sections.get("irregularity_budget") or "允许轻微断裂和回勾，不强造低级错误。").replace("\n", " ").strip(),
        anti_ai_guardrails=anti_ai_guardrails or ["禁止解释腔", "禁止总结腔", "禁止模板示范腔"],
    )


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
