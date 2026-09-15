import pytest

from core.levels import (
    TIER_HIGH,
    TIER_LOW,
    TIER_PAUSED,
    build_levels,
    highest_in_tier,
    highest_level_at_or_below,
    level_by_name,
    lowest_charging_level,
    tier_threshold_kw,
)


@pytest.fixture
def levels():
    return build_levels()


def test_levels_are_sorted_and_named(levels):
    names = [lv.name for lv in levels]
    assert names[:4] == ["off", "car_6A", "car_8A", "wb_6A"]
    assert names[-1] == "wb_16A"
    powers = [lv.power_kw for lv in levels]
    assert powers == sorted(powers)


def test_level_powers_match_spec(levels):
    assert level_by_name(levels, "car_6A").power_kw == 1.6
    assert level_by_name(levels, "car_8A").power_kw == 2.0
    assert level_by_name(levels, "wb_6A").power_kw == pytest.approx(4.14)
    assert level_by_name(levels, "wb_16A").power_kw == pytest.approx(11.04)


def test_tiers_and_commands(levels):
    off = level_by_name(levels, "off")
    assert off.tier == TIER_PAUSED and off.car_limit is None
    low = level_by_name(levels, "car_8A")
    assert low.tier == TIER_LOW and low.car_limit == "8A" and low.wb_current == 6
    high = level_by_name(levels, "wb_9A")
    assert high.tier == TIER_HIGH and high.car_limit == "Max" and high.wb_current == 9


def test_tier_threshold_is_wb_6A(levels):
    assert tier_threshold_kw(levels) == level_by_name(levels, "wb_6A").power_kw


@pytest.mark.parametrize(
    "power,expected",
    [(13.5, "wb_16A"), (7.3, "wb_10A"), (4.2, "wb_6A"), (4.1, "car_8A"), (2.4, "car_8A"), (1.6, "car_6A"), (1.1, None)],
)
def test_highest_level_at_or_below(levels, power, expected):
    lv = highest_level_at_or_below(levels, power)
    assert (lv.name if lv else None) == expected


def test_lowest_charging_level(levels):
    assert lowest_charging_level(levels).name == "car_6A"


def test_highest_in_tier_falls_back_to_lowest_of_tier(levels):
    assert highest_in_tier(levels, TIER_HIGH, 2.0).name == "wb_6A"
    assert highest_in_tier(levels, TIER_LOW, 1.0).name == "car_6A"
    assert highest_in_tier(levels, TIER_LOW, 9.0).name == "car_8A"


def test_custom_kw_per_amp():
    lv = level_by_name(build_levels(kw_per_amp=0.65), "wb_6A")
    assert lv.power_kw == 3.9
