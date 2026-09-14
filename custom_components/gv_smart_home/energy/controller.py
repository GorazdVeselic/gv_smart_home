# custom_components/gv_smart_home/energy/controller.py
from __future__ import annotations

import datetime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change

from ..helpers.calendar import (
    is_weekend,
    is_holiday,
    get_holiday_name,
    get_next_holiday,
)
from ..helpers.energy import (
    get_current_block,
    get_prev_next_block_info,
    is_high_season,
)


class EnergyController:
    """Computes block schedule, season and calendar info.
    Pushes values to coordinator whenever needed (hourly + midnight)."""

    def __init__(self, hass: HomeAssistant, coordinator):
        self.hass = hass
        self.coordinator = coordinator

    async def start(self):
        # Midnight update
        self._unsub_midnight = async_track_time_change(
            self.hass, self._handle_midnight, hour=0, minute=0, second=1
        )

        # Hourly update
        self._unsub_hourly = async_track_time_change(
            self.hass, self._handle_hourly, minute=0, second=1
        )

        # First run
        await self.update()

    async def stop(self):
        if hasattr(self, "_unsub_midnight"):
            self._unsub_midnight()
        if hasattr(self, "_unsub_hourly"):
            self._unsub_hourly()

    async def update(self):
        now = datetime.datetime.now()
        today = now.date()
        hour = now.hour

        current_block = get_current_block(today, hour)
        block_info = get_prev_next_block_info(now)
        season_high = is_high_season(today)

        # Calendar logic
        is_weekend_flag = is_weekend(today)
        is_holiday_flag = is_holiday(today)
        work_free = is_weekend_flag or is_holiday_flag

        holiday_name = get_holiday_name(today)
        next_holiday_date, next_holiday_name = get_next_holiday(today)

        await self.coordinator.async_set(
            current_block=current_block,
            next_block=block_info["next_block"],
            minutes_to_next=block_info["minutes_to_next"],
            previous_block=block_info["previous_block"],
            same_as_next=block_info["same_as_next"],
            season="high" if season_high else "low",
            is_weekend=is_weekend_flag,
            is_holiday=is_holiday_flag,
            is_work_free_day=work_free,
            holiday_name=holiday_name,
            next_holiday_name=next_holiday_name,
            next_holiday_date=(
                next_holiday_date.isoformat() if next_holiday_date else None
            ),
        )

    async def _handle_midnight(self, *_):
        await self.update()

    async def _handle_hourly(self, *_):
        await self.update()
