from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ..const import CONF_SAMPLING_INTERVAL, DEFAULT_SAMPLING_INTERVAL
from ..samplers.power_sampler import PowerSampler

_LOGGER = logging.getLogger(__name__)


class SamplingCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self.entry = entry

        sampling_interval = entry.options.get(
            CONF_SAMPLING_INTERVAL,
            entry.data.get(CONF_SAMPLING_INTERVAL, DEFAULT_SAMPLING_INTERVAL),
        )

        self.power_sampler = PowerSampler(hass)

        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name="Smart EV Sampling Coordinator",
            update_interval=timedelta(seconds=int(sampling_interval)),
        )

    async def async_start(self) -> None:
        #_LOGGER.info("Starting SamplingCoordinator (first refresh)")
        await self.async_config_entry_first_refresh()

    async def _async_update_data(self):
        #_LOGGER.debug("SamplingCoordinator tick: _async_update_data called")

        # TODO: business logic
        # - read SolarEdge power meter
        # - normalize sign (+ surplus / - deficit)
        # - push into sample buffer
        #
        # Logging here is intentional so you can confirm coordinator is ticking.
        await self.power_sampler.sample()

        # Return something so sensors can display something (even None is OK)
        return None
