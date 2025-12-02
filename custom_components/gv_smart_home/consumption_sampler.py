from __future__ import annotations

import logging
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    HC_SAMPLE_INTERVAL_SECONDS,
    HC_WINDOW_MINUTES,
    CONF_GRID_POWER_ENTITY,
    CONF_BLOCK_1,
    CONF_BLOCK_2,
    CONF_BLOCK_3,
    CONF_BLOCK_4,
    CONF_BLOCK_5,
)
from .helpers import get_current_block, get_prev_next_block_info

_LOGGER = logging.getLogger(__name__)

HC_SAMPLE_INTERVAL = timedelta(seconds=HC_SAMPLE_INTERVAL_SECONDS)
HC_MAX_SAMPLES = int((60 / HC_SAMPLE_INTERVAL_SECONDS) * HC_WINDOW_MINUTES)


class ConsumptionSampler:
    """Takes 10-second samples of grid power and block limits."""

    def __init__(self, hass: HomeAssistant, entry, coordinator):
        self.hass = hass
        self.entry = entry
        self.coordinator = coordinator
        self.samples = []
        self._unsub = None

    async def start(self):
        self._unsub = async_track_time_interval(
            self.hass, self._sample_now, HC_SAMPLE_INTERVAL
        )
        _LOGGER.debug("Sampler started")

    async def stop(self):
        if self._unsub:
            self._unsub()
            self._unsub = None

    @callback
    def _sample_now(self, _now):
        cfg = self.coordinator.config

        grid_entity = cfg.get(CONF_GRID_POWER_ENTITY)
        if not grid_entity:
            return

        state = self.hass.states.get(grid_entity)
        grid_power_w = None
        if state and state.state not in ("unknown", "unavailable"):
            try:
                grid_power_w = int(float(state.state))
            except ValueError:
                grid_power_w = None

        now_dt = datetime.now()
        block = get_current_block(now_dt.date(), now_dt.hour)
        info = get_prev_next_block_info(now_dt)

        # Read ALWAYS from dynamic config
        block_limits = {
            1: cfg.get(CONF_BLOCK_1),
            2: cfg.get(CONF_BLOCK_2),
            3: cfg.get(CONF_BLOCK_3),
            4: cfg.get(CONF_BLOCK_4),
            5: cfg.get(CONF_BLOCK_5),
        }

        current_limit_kw = block_limits[block]
        current_limit_w = int(current_limit_kw * 1000)

        next_block = info["next_block"]
        minutes_to_next = info["minutes_to_next"]
        next_limit_kw = block_limits[next_block]
        next_limit_w = int(next_limit_kw * 1000)

        self.samples.append({
            "ts": now_dt,
            "grid_power_w": grid_power_w,
            "current_block": block,
            "next_block": next_block,
            "minutes_to_next": minutes_to_next,
            "current_block_limit_w": current_limit_w,
            "next_block_limit_w": next_limit_w,
        })

        if len(self.samples) > HC_MAX_SAMPLES:
            self.samples.pop(0)
