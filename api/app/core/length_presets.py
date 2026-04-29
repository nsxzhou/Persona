"""篇幅预设配置中心。

定义短篇/中篇/长篇的参数配置，以及基于当前字数计算进度的工具函数。
"""

from __future__ import annotations

from typing import Literal, TypedDict


LengthPresetKey = Literal["short", "medium", "long"]


class LengthPresetConfig(TypedDict):
    label: str
    target_min: int
    target_max: int
    recommended_chapters: tuple[int, int]
    beat_count_default: int
    beat_count_range: tuple[int, int]
    beat_expand_chars: int
    ending_zone_ratio: float  # 达到 target_max 的此比例时进入收束区


class PlanningBudget(TypedDict):
    character_count: tuple[int, int]
    volume_count: tuple[int, int]
    first_volume_chapters: tuple[int, int]


LENGTH_PRESETS: dict[LengthPresetKey, LengthPresetConfig] = {
    "short": {
        "label": "短篇",
        "target_min": 50_000,
        "target_max": 150_000,
        "recommended_chapters": (8, 20),
        "beat_count_default": 5,
        "beat_count_range": (3, 8),
        "beat_expand_chars": 400,
        "ending_zone_ratio": 0.80,
    },
    "medium": {
        "label": "中篇",
        "target_min": 150_000,
        "target_max": 500_000,
        "recommended_chapters": (30, 80),
        "beat_count_default": 8,
        "beat_count_range": (5, 12),
        "beat_expand_chars": 500,
        "ending_zone_ratio": 0.85,
    },
    "long": {
        "label": "长篇",
        "target_min": 500_000,
        "target_max": 2_000_000,
        "recommended_chapters": (100, 400),
        "beat_count_default": 8,
        "beat_count_range": (5, 15),
        "beat_expand_chars": 500,
        "ending_zone_ratio": 0.90,
    },
}

PLANNING_BUDGETS: dict[LengthPresetKey, PlanningBudget] = {
    "short": {
        "character_count": (6, 9),
        "volume_count": (3, 5),
        "first_volume_chapters": (8, 15),
    },
    "medium": {
        "character_count": (10, 14),
        "volume_count": (5, 8),
        "first_volume_chapters": (12, 25),
    },
    "long": {
        "character_count": (14, 22),
        "volume_count": (8, 12),
        "first_volume_chapters": (20, 40),
    },
}

ProgressPhase = Literal["writing", "ending_zone", "over_target"]


class LengthProgress(TypedDict):
    current_chars: int
    target_min: int
    target_max: int
    percentage: float
    phase: ProgressPhase


def get_planning_budget(preset_key: LengthPresetKey) -> PlanningBudget:
    """返回初始化规划阶段使用的软预算。"""
    return PLANNING_BUDGETS[preset_key]


def get_progress(content_length: int, preset_key: LengthPresetKey) -> LengthProgress:
    """根据当前字数和篇幅预设计算进度状态。"""
    cfg = LENGTH_PRESETS[preset_key]
    pct = content_length / cfg["target_max"]
    if pct >= 1.0:
        phase: ProgressPhase = "over_target"
    elif pct >= cfg["ending_zone_ratio"]:
        phase = "ending_zone"
    else:
        phase = "writing"
    return {
        "current_chars": content_length,
        "target_min": cfg["target_min"],
        "target_max": cfg["target_max"],
        "percentage": round(pct * 100, 1),
        "phase": phase,
    }
