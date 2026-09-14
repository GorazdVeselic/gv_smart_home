from __future__ import annotations

import logging
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class ChargingController:
    def __init__(self, hass: HomeAssistant):
        self.hass = hass

    async def heartbeat(self) -> None:
        _LOGGER.debug("ChargingController.heartbeat called")

        # TODO: business logic
        # - later: validate charger availability
        # - later: call HA service to set amps
        return None

    async def set_current(self, amps: int) -> None:
        _LOGGER.info("ChargingController.set_current called with %s A", amps)

        # TODO: business logic
        # - call charger integration service
        return None
