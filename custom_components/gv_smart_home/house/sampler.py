# custom_components/gv_smart_home/house/sampler.py
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.config_entries import ConfigEntry

from ..const import (
    HC_SAMPLE_INTERVAL_SECONDS,
    CONF_GRID_POWER_ENTITY,
)
from ..coordinator import GVChargingCoordinator
from ..controller.house_controller import HouseController

_LOGGER = logging.getLogger(__name__)

HC_SAMPLE_INTERVAL = timedelta(seconds=HC_SAMPLE_INTERVAL_SECONDS)


class HouseSampler:
    """
    Periodically samples grid power and stores it in the HouseController.

    Responsibilities:
      - read CONF_GRID_POWER_ENTITY
      - extract numeric grid power
      - push sample {'ts', 'grid_power_w'} into house_controller
      - NO other logic (no blocks, no limits, no season)
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: GVChargingCoordinator,
        house_controller: HouseController,
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.coordinator = coordinator
        self.house_controller = house_controller
        self._unsub = None

    async def start(self) -> None:
        """Start taking periodic grid samples."""
        self._unsub = async_track_time_interval(
            self.hass,
            self._sample_now,
            HC_SAMPLE_INTERVAL
        )
        _LOGGER.debug("HouseSampler started")

    async def stop(self) -> None:
        """Stop sampling."""
        if self._unsub:
            self._unsub()
            self._unsub = None
        _LOGGER.debug("HouseSampler stopped")

    @callback
    def _sample_now(self, _now) -> None:
        """Take one numeric sample of grid power."""
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

        self.house_controller.add_sample({
            "ts": datetime.now(),
            "grid_power_w": grid_power_w,
        })
