import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

class GVChargingCoordinator(DataUpdateCoordinator):
    """Stores computed values from the EV controller."""

    def __init__(self, hass: HomeAssistant):
        super().__init__(
            hass,
            _LOGGER,
            name="GV Smart Home Charging Coordinator",
            update_interval=None,  # PUSH-BASED, controller updates it
        )
        self.data = {}

    async def async_set(self, **values):
        """Update data and notify listeners (sensor entities)."""
        self.data.update(values)
        self.async_set_updated_data(self.data)
