# custom_components/gv_smart_home/controller/energy_controller.py
from __future__ import annotations

import datetime
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from ..helpers.energy import (
    is_high_season,
    get_current_block,
    get_prev_next_block_info,
    get_blocks_for_today,
)
from ..helpers.calendar import (
    is_weekend,
    is_holiday,
    get_holiday_name,
    get_next_holiday,
)
from ..const import (
    CONF_BLOCK_1,
    CONF_BLOCK_2,
    CONF_BLOCK_3,
    CONF_BLOCK_4,
    CONF_BLOCK_5,
)


class EnergyController:
    """
    Centralized energy tariff logic and block limit calculations.
    - current_block / next_block
    - minutes_to_next
    - season, weekend, holiday
    - 24-hour block plan
    - current_limit_w / next_limit_w
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.data: dict = {}

    @property
    def latest(self) -> dict:
        """Return last computed data."""
        return self.data

    # ------------------------------------------------------------------
    # MAIN UPDATE
    # ------------------------------------------------------------------
    async def async_update(self) -> dict:
        """Compute full energy status."""
        now = datetime.datetime.now()
        today = now.date()
        hour = now.hour

        # Core block transitions
        block_info = get_prev_next_block_info(now)

        current_block = block_info["current_block"]
        next_block = block_info["next_block"]
        previous_block = block_info["previous_block"]
        minutes_to_next = block_info["minutes_to_next"]

        # Seasonal classification
        high_season = is_high_season(today)
        season = "high" if high_season else "low"

        # Weekend / holiday
        weekend = is_weekend(today)
        holiday = is_holiday(today)
        work_free = weekend or holiday

        holiday_name = get_holiday_name(today)
        next_holiday_date, next_holiday_name = get_next_holiday(today)

        # Tariff block plan for today (list of 24 ints)
        block_plan = get_blocks_for_today(today)

        # Dynamic block power limits from user config
        cfg = {**self.entry.data, **self.entry.options}

        block_limits_kw = {
            1: cfg.get(CONF_BLOCK_1),
            2: cfg.get(CONF_BLOCK_2),
            3: cfg.get(CONF_BLOCK_3),
            4: cfg.get(CONF_BLOCK_4),
            5: cfg.get(CONF_BLOCK_5),
        }

        # Convert to W
        current_limit_kw = block_limits_kw[current_block]
        next_limit_kw = block_limits_kw[next_block]

        current_limit_w = int(current_limit_kw * 1000)
        next_limit_w = int(next_limit_kw * 1000)

        self.data = {
            # MAIN BLOCK VALUES
            "current_block": current_block,
            "next_block": next_block,
            "previous_block": previous_block,
            "minutes_to_next": minutes_to_next,

            # LIMITS
            "current_limit_w": current_limit_w,
            "next_limit_w": next_limit_w,

            # SEASON
            "is_high_season": high_season,
            "season": season,

            # DAY TYPE
            "is_weekend": weekend,
            "is_holiday": holiday,
            "is_work_free_day": work_free,

            # HOLIDAY META
            "holiday_name": holiday_name,
            "next_holiday_name": next_holiday_name,
            "next_holiday_date": (
                next_holiday_date.isoformat() if next_holiday_date else None
            ),

            # META
            "same_as_previous": block_info["same_as_previous"],
            "same_as_next": block_info["same_as_next"],
            "minutes_since_previous": block_info["minutes_since_previous"],

            # FULL DAY
            "blocks": block_plan,
        }

        return self.data
