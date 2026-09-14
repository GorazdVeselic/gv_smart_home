# custom_components/gv_smart_home/controller/wallbox_controller.py
from __future__ import annotations

from dataclasses import dataclass
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from ..coordinator import GVChargingCoordinator
from ..const import (
    CONF_WB_CABLE,
    CONF_WB_STATUS,
)


@dataclass
class WallboxState:
    available: bool
    state: str
    reasons: list[str]
    cable_connected: bool | None
    raw_status: str | None


class WallboxController:
    """
    Evaluates Wallbox state based on two entities:
      - cable connected (binary_sensor)
      - charging status (sensor)
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: GVChargingCoordinator,
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.coordinator = coordinator
        self.data: dict = {}

    @property
    def latest(self) -> dict:
        return self.data

    # ----------------------------------------------------------------------
    # UPDATE
    # ----------------------------------------------------------------------
    async def async_update(self) -> dict:
        cfg = self.coordinator.config

        cable_ent = cfg.get(CONF_WB_CABLE)
        status_ent = cfg.get(CONF_WB_STATUS)

        cable = self._get_state(cable_ent)
        status = self._get_state(status_ent)

        reasons: list[str] = []

        # Cable
        cable_connected = None
        if cable is not None:
            cable_connected = cable == "on"
            if not cable_connected:
                reasons.append("cable_disconnected")
        else:
            reasons.append("cable_unknown")

        # Status evaluation
        state: str
        if status is None:
            reasons.append("status_unknown")
            state = "idle"
        elif status in ("fault", "error"):
            state = "error"
            reasons.append(f"status_{status}")
        elif status == "charging":
            state = "charging"
        elif status == "ready":
            state = "ready"
        else:
            state = "idle"

        available = len(reasons) == 0 or (
            "cable_unknown" not in reasons
            and "status_unknown" not in reasons
        )

        result = WallboxState(
            available=available,
            state=state,
            reasons=reasons,
            cable_connected=cable_connected,
            raw_status=status,
        )

        # store internal representation for sensors
        self.data = {
            "wb_available": result.available,
            "wb_state": result.state,
            "wb_reasons": result.reasons,
            "wb_cable_connected": result.cable_connected,
            "wb_status_raw": result.raw_status,
        }

        return self.data

    # ----------------------------------------------------------------------
    # HELPERS
    # ----------------------------------------------------------------------
    def _get_state(self, entity_id: str | None) -> str | None:
        if not entity_id:
            return None

        st = self.hass.states.get(entity_id)
        if not st or st.state in ("unknown", "unavailable"):
            return None

        return st.state
