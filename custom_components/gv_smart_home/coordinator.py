from __future__ import annotations
import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class GVChargingCoordinator(DataUpdateCoordinator):
    """Coordinator for EV charging logic and configuration access."""

    def __init__(self, hass: HomeAssistant, entry):
        super().__init__(
            hass,
            _LOGGER,
            name="GV Smart Home Charging Coordinator",
            update_interval=None,
        )
        self.hass = hass
        self.entry = entry
        self.data = {}

    # ------------------------------------------------------------------
    # REQUIRED BY DataUpdateCoordinator (for CoordinatorEntity support)
    # ------------------------------------------------------------------
    async def _async_update_data(self):
        """Needed only for CoordinatorEntity compatibility.

        Our coordinator is push-based, so polling should return existing data.
        """
        return self.data

    # ------------------------------------------------------------------
    # RUNTIME CONFIG ACCESS (MERGED)
    # ------------------------------------------------------------------
    @property
    def config(self) -> dict:
        """Merged config (options override data)."""
        return {**self.entry.data, **self.entry.options}

    def get(self, key, default=None):
        """Helper for safe key access."""
        return self.config.get(key, default)

    # ------------------------------------------------------------------
    # Values pushed by controller
    # ------------------------------------------------------------------
    async def async_set(self, **values):
        """Push sensor updates and notify listeners."""
        self.data.update(values)
        self.async_set_updated_data(self.data)
