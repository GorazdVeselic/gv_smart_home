from __future__ import annotations

import datetime
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

class EnergyCoordinator(DataUpdateCoordinator):
    """Coordinates updates from the EnergyController."""

    def __init__(self, hass, entry, controller):
        super().__init__(
            hass,
            logger=__name__,
            name="GV Smart Home Energy Coordinator",
            update_interval=datetime.timedelta(seconds=60),
        )
        self.hass = hass
        self.entry = entry
        self.controller = controller

    async def _async_update_data(self):
        """Fetch and return updated data from controller."""
        return await self.controller.async_update()
