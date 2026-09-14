"""Stopnje moči polnjenja (spec 6.3).

Dve ravni:
- `low`: tok omejuje avto (6A ali 8A). Meja avta je skupni tok čez vse 3 faze,
  zato 6A pomeni 1,6 kW in 8A 2,0 kW (izmerjeno 2026-09-14). Preklop gre prek
  SAIC oblaka, 15 do 20 s.
- `high`: avto na Max, tok omejuje wallbox na fazo, 6 do 16 A, takoj.

`off` je pavza (wallbox enable off), raven `paused`.
"""

from __future__ import annotations

from dataclasses import dataclass

TIER_PAUSED = "paused"
TIER_LOW = "low"
TIER_HIGH = "high"

CAR_LIMIT_MAX = "Max"

# Izmerjena moč pri meji avta (kW). Ključ je vrednost izbirnika v avtu.
CAR_LEVEL_POWER_KW = {"6A": 1.6, "8A": 2.0}

# Wallbox v ravni low stoji na tej vrednosti, avto omejuje sam.
WB_CURRENT_IN_LOW_TIER = 8

DEFAULT_KW_PER_AMP = 0.69
DEFAULT_WB_MIN_CURRENT = 6
DEFAULT_WB_MAX_CURRENT = 16


@dataclass(frozen=True)
class Level:
    name: str
    tier: str
    car_limit: str | None
    wb_current: int
    power_kw: float


def build_levels(
    kw_per_amp: float = DEFAULT_KW_PER_AMP,
    wb_min_current: int = DEFAULT_WB_MIN_CURRENT,
    wb_max_current: int = DEFAULT_WB_MAX_CURRENT,
) -> list[Level]:
    """Vrne stopnje urejene od najnižje do najvišje moči."""
    levels = [Level("off", TIER_PAUSED, None, wb_min_current, 0.0)]
    for car_limit, power in CAR_LEVEL_POWER_KW.items():
        levels.append(
            Level(f"car_{car_limit}", TIER_LOW, car_limit, WB_CURRENT_IN_LOW_TIER, power)
        )
    for amps in range(wb_min_current, wb_max_current + 1):
        levels.append(
            Level(f"wb_{amps}A", TIER_HIGH, CAR_LIMIT_MAX, amps, round(amps * kw_per_amp, 2))
        )
    levels.sort(key=lambda lv: lv.power_kw)
    return levels


def tier_threshold_kw(levels: list[Level]) -> float:
    """Moč najnižje stopnje ravni high (P_tier v specu)."""
    return min(lv.power_kw for lv in levels if lv.tier == TIER_HIGH)


def lowest_charging_level(levels: list[Level]) -> Level:
    """Najnižja stopnja, ki še polni (car_6A)."""
    return min((lv for lv in levels if lv.tier != TIER_PAUSED), key=lambda lv: lv.power_kw)


def highest_level_at_or_below(levels: list[Level], power_kw: float) -> Level | None:
    """Najvišja stopnja, ki polni z močjo <= power_kw. None, kadar nobena ne gre."""
    candidates = [lv for lv in levels if lv.tier != TIER_PAUSED and lv.power_kw <= power_kw]
    if not candidates:
        return None
    return max(candidates, key=lambda lv: lv.power_kw)


def level_by_name(levels: list[Level], name: str) -> Level:
    for lv in levels:
        if lv.name == name:
            return lv
    raise KeyError(name)


def highest_in_tier(levels: list[Level], tier: str, power_kw: float) -> Level | None:
    """Najvišja stopnja znotraj dane ravni z močjo <= power_kw, sicer najnižja te ravni."""
    in_tier = [lv for lv in levels if lv.tier == tier]
    if not in_tier:
        return None
    fitting = [lv for lv in in_tier if lv.power_kw <= power_kw]
    if fitting:
        return max(fitting, key=lambda lv: lv.power_kw)
    return min(in_tier, key=lambda lv: lv.power_kw)
