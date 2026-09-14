from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from ..controllers.charging_controller import ChargingController
from ..const import DEFAULT_CONTROL_INTERVAL

_LOGGER = logging.getLogger(__name__)


class ControlCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self.entry = entry

        self.charging_controller = ChargingController(hass)

        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name="Smart EV Control Coordinator",
            update_interval=timedelta(seconds=DEFAULT_CONTROL_INTERVAL),
        )

    async def async_start(self) -> None:
        #_LOGGER.info("Starting ControlCoordinator (first refresh)")
        await self.async_config_entry_first_refresh()

    async def _async_update_data(self):
        _LOGGER.debug("ControlCoordinator tick: _async_update_data called")

        # TODO: business logic
        # - compute allowed charging current
        # - enforce contracted power
        # - call controller with desired amps
        #
        # Example log-only call (no business logic):
        await self.charging_controller.heartbeat()

        return None
