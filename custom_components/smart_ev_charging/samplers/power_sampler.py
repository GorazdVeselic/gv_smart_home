from __future__ import annotations

import logging
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class PowerSampler:
    def __init__(self, hass: HomeAssistant):
        self.hass = hass

    async def sample(self) -> None:
        _LOGGER.debug("PowerSampler.sample called")

        # TODO: business logic
        # - read HA entity state (SolarEdge power meter)
        # - parse numeric power
        # - return/store value
        return None
