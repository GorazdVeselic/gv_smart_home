# custom_components/gv_smart_home/controller/mg4_controller.py
from __future__ import annotations

from dataclasses import dataclass
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from ..coordinator import GVChargingCoordinator
from ..const import (
    CONF_MG_GUN_STATE,
    CONF_MG_ACTIVE,
    CONF_MG_SET_CURRENT,
)


@dataclass
class MG4State:
    available: bool
    state: str
    reasons: list[str]
    gun_connected: bool | None
    charging_active: bool | None
    current_limit: int | None    # interpreted numeric limit (A)
    current_raw: str | None      # raw text from select/number


class MG4Controller:
    """
    Evaluates MG4 charging state based on:
      - gun connected?
      - charging active?
      - selected current limit?
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

        gun_ent = cfg.get(CONF_MG_GUN_STATE)
        active_ent = cfg.get(CONF_MG_ACTIVE)
        current_ent = cfg.get(CONF_MG_SET_CURRENT)

        # Raw states
        gun = self._get_state(gun_ent)          # "on"/"off"/None
        active = self._get_state(active_ent)    # "on"/"off"/None
        current_raw = self._get_state(current_ent)  # e.g. "6", "7", "max", None

        # Derived
        gun_connected = None
        charging_active = None
        current_limit = None

        reasons: list[str] = []

        # GUN CONNECTED
        if gun is None:
            reasons.append("gun_unknown")
        else:
            gun_connected = gun == "on"
            if not gun_connected:
                reasons.append("gun_disconnected")

        # ACTIVE CHARGING (switch)
        if active is None:
            reasons.append("active_unknown")
        else:
            charging_active = active == "on"

        # CURRENT LIMIT
        if current_raw is None:
            reasons.append("limit_unknown")
        else:
            try:
                current_limit = int(float(current_raw))
            except Exception:
                current_limit = None
                reasons.append(f"invalid_limit_{current_raw}")

        # STATE LOGIC
        if charging_active:
            state = "charging"
        elif gun_connected:
            state = "ready"
        else:
            state = "idle"

        available = len(reasons) == 0 or (
            "gun_unknown" not in reasons
            and "active_unknown" not in reasons
        )

        result = MG4State(
            available=available,
            state=state,
            reasons=reasons,
            gun_connected=gun_connected,
            charging_active=charging_active,
            current_limit=current_limit,
            current_raw=current_raw,
        )

        self.data = {
            "mg_available": result.available,
            "mg_state": result.state,
            "mg_reasons": result.reasons,
            "mg_gun_connected": result.gun_connected,
            "mg_charging_active": result.charging_active,
            "mg_current_limit": result.current_limit,
            "mg_set_current_raw": result.current_raw,
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
