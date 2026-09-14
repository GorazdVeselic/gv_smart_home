# custom_components/gv_smart_home/mg4/controller.py
from __future__ import annotations

from homeassistant.core import HomeAssistant

from ..const import (
    CONF_MG_ACTIVE,
    CONF_MG_GUN_STATE,
    CONF_MG_SET_CURRENT,
)


class MG4Controller:
    """Reads MG4 states and computes MG4 availability."""

    def __init__(self, hass: HomeAssistant, coordinator):
        self.hass = hass
        self.coordinator = coordinator

    async def update(self):
        cfg = self.coordinator.config

        gun = self._get(cfg.get(CONF_MG_GUN_STATE))
        active = self._get(cfg.get(CONF_MG_ACTIVE))
        limit_raw = cfg.get(CONF_MG_SET_CURRENT)

        available = gun == "on"

        await self.coordinator.async_set(
            mg_gun_connected=available,
            mg_charging_active=(active == "on"),
            mg_set_current_raw=limit_raw,
            mg_available=available,
        )

    def _get(self, entity_id):
        if not entity_id:
            return None
        st = self.hass.states.get(entity_id)
        if not st or st.state in ("unknown", "unavailable"):
            return None
        return st.state
