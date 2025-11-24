# sampler.py
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

# Derived values
HC_SAMPLE_INTERVAL = timedelta(seconds=HC_SAMPLE_INTERVAL_SECONDS)
# Samples fitting in the sliding window
HC_MAX_SAMPLES = int((60 / HC_SAMPLE_INTERVAL_SECONDS) * HC_WINDOW_MINUTES)

class ConsumptionSampler:
    """Stores 5-second samples of house consumption."""

    def __init__(self, hass: HomeAssistant, config_entry):
        self.hass = hass
        self.entry = config_entry
        self.samples: list[dict] = []  # circular buffer
        self.grid_power_entity = config_entry.data.get(CONF_GRID_POWER_ENTITY)

        # Block power limits from config (kW)
        self.block_limits = {
            1: config_entry.data.get(CONF_BLOCK_1),
            2: config_entry.data.get(CONF_BLOCK_2),
            3: config_entry.data.get(CONF_BLOCK_3),
            4: config_entry.data.get(CONF_BLOCK_4),
            5: config_entry.data.get(CONF_BLOCK_5),
        }

        self._unsub = None

    async def start(self):
        """Start sampler."""
        self._unsub = async_track_time_interval(
            self.hass, self._sample_now, HC_SAMPLE_INTERVAL
        )

    async def stop(self):
        """Stop sampler."""
        if self._unsub:
            self._unsub()
            self._unsub = None

    @callback
    def _sample_now(self, now):
        """Read entity and store 5-second sample."""
        if not self.grid_power_entity:
            return

        grid_powwe_state = self.hass.states.get(self.grid_power_entity)
        grid_power_w = None
        if grid_powwe_state and grid_powwe_state.state not in ("unknown", "unavailable"):
            try:
                grid_power_w = int(float(grid_powwe_state.state))
            except ValueError:
                grid_power_w = None

        # 2) tariff block logic via helpers
        now_dt = datetime.now()
        block = get_current_block(now_dt.date(), now_dt.hour)
        info = get_prev_next_block_info(now_dt)

        # 3) block power limit
        current_block_limit_kw = self.block_limits[block]
        current_block_limit_w = int(current_block_limit_kw * 1000)

        next_block = info["next_block"]
        minutes_to_next = info["minutes_to_next"]
        next_block_limit_kw = self.block_limits[next_block]
        next_block_limit_w = int(next_block_limit_kw * 1000)

        self.samples.append({
            "ts": now_dt,
            "grid_power_w": grid_power_w,
            "current_block": block,
            "next_block": next_block,
            "minutes_to_next": minutes_to_next,
            "current_block_limit_w": current_block_limit_w,
            "next_block_limit_w": next_block_limit_w,
        })

        if len(self.samples) > HC_MAX_SAMPLES:
            self.samples.pop(0)
        #
        # _LOGGER.debug(
        #     f"Sample: "
        #     f"house={grid_power_w}W "
        #     f"(samples={len(self.samples)})"
        # )
        return
        _LOGGER.debug(
            f"Sample: "
            f"house={grid_power_w}W "
            f"block={block} "
            f"limit={current_block_limit_w}W "
            f"next={next_block} "
            f"in {minutes_to_next}min "
            f"(samples={len(self.samples)})"
        )

    def get_samples(self) -> list[dict]:
        """Return in-memory 5s samples."""
        return self.samples
