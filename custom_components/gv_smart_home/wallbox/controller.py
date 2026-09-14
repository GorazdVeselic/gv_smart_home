# custom_components/gv_smart_home/wallbox/controller.py
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from ..const import (
    CONF_WB_POWER,
    CONF_WB_SET_CURRENT,
    CONF_WB_CABLE,
    CONF_WB_STATUS,
)


class WallboxController:
    """Reads raw wallbox entities and derives availability/state."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, coordinator):
        self.hass = hass
        self.entry = entry
        self.coordinator = coordinator

    async def update(self):
        cfg = self.coordinator.config

        power = self._get(cfg.get(CONF_WB_POWER))
        cable = self._get(cfg.get(CONF_WB_CABLE))
        status = self._get(cfg.get(CONF_WB_STATUS))
        set_current_entity = cfg.get(CONF_WB_SET_CURRENT)

        available = cable == "on" and status not in ("fault", "error", None)

        await self.coordinator.async_set(
            wb_power_w=int(power) if power not in (None, "") else None,
            wb_status_raw=status,
            wb_cable_connected=cable == "on",
            wb_available=available,
            wb_set_current_entity=set_current_entity,
        )

    def _get(self, entity_id):
        if not entity_id:
            return None
        st = self.hass.states.get(entity_id)
        if not st or st.state in ("unknown", "unavailable"):
            return None
        return st.state
