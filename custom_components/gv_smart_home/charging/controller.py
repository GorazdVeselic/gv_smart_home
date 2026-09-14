# custom_components/gv_smart_home/charging/controller.py
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from ..const import CC_INTERVAL_MINUTES, RAMP_UP_MAX_STEP_W, RAMP_DOWN_MINUTES_BEFORE

_LOGGER = logging.getLogger(__name__)
INTERVAL = timedelta(minutes=CC_INTERVAL_MINUTES)


class HomeChargingController:
    """Main EV charging logic that merges all data sources."""

    def __init__(self, hass: HomeAssistant, sampler, energy, wallbox, mg4, coordinator):
        self.hass = hass
        self.sampler = sampler
        self.energy = energy
        self.wallbox = wallbox
        self.mg4 = mg4
        self.coordinator = coordinator

        self.last_power = 0
        self._unsub = None

    async def start(self):
        self._unsub = async_track_time_interval(
            self.hass, self._tick, INTERVAL
        )
        _LOGGER.debug("Charging controller started")

    async def stop(self):
        if self._unsub:
            self._unsub()
            self._unsub = None

    async def _tick(self, *_):
        # Update dependent modules
        await self.energy.update()
        await self.wallbox.update()
        await self.mg4.update()

        # No samples yet → cannot compute
        if not self.sampler.samples:
            return

        now = datetime.now()
        avg = self._avg_power()

        cd = self.coordinator.data
        current_limit_w = cd.get("current_block_limit_w")
        next_limit_w = cd.get("next_block_limit_w")
        minutes_to_next = cd.get("minutes_to_next")

        effective_limit = self._effective_limit(
            current_limit_w,
            next_limit_w,
            minutes_to_next
        )

        available = max(int(effective_limit + avg), 0)
        target_power = self._apply_ramp(available)

        # If no chargers available, set 0
        if not cd.get("wb_available") and not cd.get("mg_available"):
            target_power = 0

        await self.coordinator.async_set(
            avg_grid_power_w=avg,
            effective_limit_w=effective_limit,
            available_power_w=available,
            target_power_w=target_power,
        )

    def _avg_power(self):
        cutoff = datetime.now() - timedelta(minutes=15)
        vals = [
            s["grid_power_w"] for s in self.sampler.samples
            if s["grid_power_w"] is not None and s["ts"] > cutoff
        ]
        if not vals:
            return 0
        return int(sum(vals) / len(vals))

    def _effective_limit(self, curr, nxt, minutes):
        if minutes is None:
            return curr
        if nxt < curr and minutes <= RAMP_DOWN_MINUTES_BEFORE:
            return nxt
        return curr

    def _apply_ramp(self, new):
        old = self.last_power
        if new == old:
            return new
        if new < old:
            self.last_power = new
            return new
        ramped = min(new, old + RAMP_UP_MAX_STEP_W)
        self.last_power = ramped
        return ramped
