"""篇幅预设配置 get_progress() 的单元测试。"""

import pytest

from app.core import length_presets
from app.core.length_presets import LENGTH_PRESETS, get_progress


def _get_planning_budget(preset_key: str):
    assert hasattr(length_presets, "get_planning_budget")
    return length_presets.get_planning_budget(preset_key)


class TestGetProgress:
    """测试 get_progress 函数的三个 phase 判定。"""

    def test_writing_phase_zero(self):
        result = get_progress(0, "short")
        assert result["phase"] == "writing"
        assert result["percentage"] == 0.0
        assert result["target_min"] == 50_000
        assert result["target_max"] == 150_000

    def test_writing_phase_mid(self):
        result = get_progress(50_000, "short")
        assert result["phase"] == "writing"
        assert result["percentage"] == 33.3

    def test_ending_zone_at_threshold(self):
        # short ending_zone_ratio = 0.80, target_max = 150_000
        # 80% of 150_000 = 120_000
        result = get_progress(120_000, "short")
        assert result["phase"] == "ending_zone"
        assert result["percentage"] == 80.0

    def test_ending_zone_above_threshold(self):
        result = get_progress(125_000, "short")
        assert result["phase"] == "ending_zone"

    def test_over_target_at_max(self):
        result = get_progress(150_000, "short")
        assert result["phase"] == "over_target"
        assert result["percentage"] == 100.0

    def test_over_target_beyond_max(self):
        result = get_progress(160_000, "short")
        assert result["phase"] == "over_target"
        assert result["percentage"] == 106.7

    def test_just_below_ending_zone(self):
        # 79.9% of 150_000 = 119_850
        result = get_progress(119_850, "short")
        assert result["phase"] == "writing"

    def test_medium_preset(self):
        # medium: target_max=500_000, ending_zone_ratio=0.85
        # 85% of 500_000 = 425_000
        result = get_progress(425_000, "medium")
        assert result["phase"] == "ending_zone"
        assert result["target_min"] == 150_000
        assert result["target_max"] == 500_000

    def test_long_preset(self):
        # long: target_max=2_000_000, ending_zone_ratio=0.90
        # 90% of 2_000_000 = 1_800_000
        result = get_progress(1_800_000, "long")
        assert result["phase"] == "ending_zone"

    def test_all_presets_exist(self):
        assert set(LENGTH_PRESETS.keys()) == {"short", "medium", "long"}

    def test_current_chars_matches_input(self):
        result = get_progress(42_000, "short")
        assert result["current_chars"] == 42_000


class TestGetPlanningBudget:
    """测试创作规划预算随篇幅预设变化。"""

    def test_short_planning_budget(self):
        budget = _get_planning_budget("short")
        assert budget["character_count"] == (6, 9)
        assert budget["volume_count"] == (3, 5)
        assert budget["first_volume_chapters"] == (8, 15)

    def test_medium_planning_budget(self):
        budget = _get_planning_budget("medium")
        assert budget["character_count"] == (10, 14)
        assert budget["volume_count"] == (5, 8)
        assert budget["first_volume_chapters"] == (12, 25)

    def test_long_planning_budget(self):
        budget = _get_planning_budget("long")
        assert budget["character_count"] == (14, 22)
        assert budget["volume_count"] == (8, 12)
        assert budget["first_volume_chapters"] == (20, 40)
