"""EV Charging Controller for GV Smart Home."""
from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.config_entries import ConfigEntry

from .coordinator import GVChargingCoordinator

from .const import (
    CONF_WB_ACTIVE,
    CONF_WB_POWER,
    CONF_WB_SET_CURRENT,
    CONF_WB_CABLE,
    CONF_WB_STATUS,
    CONF_MG_ACTIVE,
    CONF_MG_SET_CURRENT,
    CONF_MG_GUN_STATE,
    CC_INTERVAL_MINUTES,
    RAMP_DOWN_MINUTES_BEFORE,
    RAMP_UP_MAX_STEP_W,
    HC_WINDOW_MINUTES,
)

_LOGGER = logging.getLogger(__name__)

# Sampling configuration
CONTROL_INTERVAL = timedelta(minutes=CC_INTERVAL_MINUTES)

@dataclass
class ChargerState:
    """Simple representation of Wallbox/MG4 real availability."""

    available: bool
    state: str
    reasons: list[str]


class HomeChargingController:
    """Main controller for EV charging logic."""

    def __init__(
        self,
        hass: HomeAssistant,
        sampler,
        config_entry: ConfigEntry,
        coordinator: GVChargingCoordinator
    ) -> None:
        self.hass = hass
        self.sampler = sampler
        self.samples: deque = sampler.samples
        self.config_entry = config_entry
        self.coordinator = coordinator

        self.last_target_power_w = 0

        data = config_entry.data
        self.wb_active_entity = data.get(CONF_WB_ACTIVE)
        self.wb_power_entity = data.get(CONF_WB_POWER)
        self.wb_set_current_entity = data.get(CONF_WB_SET_CURRENT)
        self.wb_cable_entity = data.get(CONF_WB_CABLE)
        self.wb_status_entity = data.get(CONF_WB_STATUS)

        self.mg_active_entity = data.get(CONF_MG_ACTIVE)
        self.mg_set_current_entity = data.get(CONF_MG_SET_CURRENT)
        self.mg_gun_state_entity = data.get(CONF_MG_GUN_STATE)

        self._unsub_control = None

    # Public entrypoint
    def start(self) -> None:
        """Start 1-minute background control loop."""
        _LOGGER.debug("controller: start!")
        self._unsub_control = async_track_time_interval(
            self.hass,
            self.async_control_tick,
            CONTROL_INTERVAL,
        )
        _LOGGER.info("HomeChargingController started")

    def stop(self) -> None:
        """Stop control loop."""
        _LOGGER.debug("controller: stop!")
        if self._unsub_control:
            self._unsub_control()
            self._unsub_control = None
            _LOGGER.info("HomeChargingController stopped")

    # Control Tick (1 min)
    async def async_control_tick(self, _now: datetime) -> None:
        _LOGGER.debug("controller: TICK!")
        """Main charging control loop executed every minute."""
        if not self.samples:
            _LOGGER.debug("controller: no samples yet")
            return

        # negative grid power is import!
        avg_grid_power_w = self.compute_average_grid_power()
        if avg_grid_power_w is None:
            _LOGGER.debug("controller: no valid grid power samples")
            return

        latest = self.samples[-1]
        current_block = latest["current_block"]
        next_block = latest["next_block"]
        minutes_to_next = latest["minutes_to_next"]
        current_limit_w = latest["current_block_limit_w"]
        next_limit_w = latest["next_block_limit_w"]

        effective_limit_w = self.compute_effective_limit(
            current_limit_w=current_limit_w,
            next_limit_w=next_limit_w,
            minutes_to_next=minutes_to_next,
        )

        # negative average grid power is import!
        available_power_w = max(int(effective_limit_w + avg_grid_power_w), 0)


        target_power_w = self.apply_ramp(available_power_w)

        wb_state = self.evaluate_wallbox_state()
        mg_state = self.evaluate_mg4_state()

        _LOGGER.info(
            "controller: block=%s eff_limit=%sW avg_grid=%.1fW avail=%sW target=%sW wb=%s mg=%s",
            current_block,
            effective_limit_w,
            avg_grid_power_w,
            available_power_w,
            target_power_w,
            wb_state.state,
            mg_state.state,
        )

        await self.coordinator.async_set(
            avg_grid_power_w=avg_grid_power_w,
            effective_limit_w=effective_limit_w,
            available_power_w=available_power_w,
            target_power_w=target_power_w,
            current_block=current_block,
            next_block=next_block,
            minutes_to_next=minutes_to_next,
        )

        if not wb_state.available and not mg_state.available:
            _LOGGER.info("controller: no chargers available → 0W")
            await self.async_apply_charging_power(0)
            return

        await self.async_apply_charging_power(target_power_w)

    # Core calculations
    def compute_average_grid_power(self) -> Optional[float]:
        cutoff = datetime.now() - timedelta(minutes=HC_WINDOW_MINUTES)
        values = [
            float(s["grid_power_w"])
            for s in self.samples
            if s.get("ts") and s.get("grid_power_w") is not None and s["ts"] >= cutoff
        ]
        if not values:
            return None
        return round(sum(values) / len(values))

    def compute_effective_limit(
        self,
        current_limit_w: int,
        next_limit_w: int,
        minutes_to_next: Optional[int],
    ) -> int:
        if minutes_to_next is None:
            return current_limit_w

        # ramp-down early if next block has lower limit
        if next_limit_w < current_limit_w and minutes_to_next <= RAMP_DOWN_MINUTES_BEFORE:
            return next_limit_w

        # keep current limit, ramp-up handled separately
        return current_limit_w

    def apply_ramp(self, new_power: int) -> int:
        old = self.last_target_power_w

        if new_power == old:
            return old

        # ramp-down instantly for safety
        if new_power < old:
            self.last_target_power_w = new_power
            return new_power

        # ramp-up gradually
        max_allowed = old + RAMP_UP_MAX_STEP_W
        ramped = min(new_power, max_allowed)
        self.last_target_power_w = ramped
        return ramped

    # Charger state evaluation
    def evaluate_wallbox_state(self) -> ChargerState:
        if not self.wb_status_entity and not self.wb_cable_entity:
            return ChargerState(False, "unavailable", ["no_entities"])

        cable = self.get_state(self.wb_cable_entity)
        status = self.get_state(self.wb_status_entity)

        reasons = []

        if cable in (None, "disconnected", "off", "false"):
            reasons.append("cable_disconnected")

        if status in ("fault", "error", None):
            if status != "ready" and status != "charging":
                reasons.append(f"status_{status}")

        state = "charging" if status == "charging" else ("ready" if not reasons else "idle")
        return ChargerState(not reasons, state, reasons)

    def evaluate_mg4_state(self) -> ChargerState:
        gun = self.get_state(self.mg_gun_state_entity)
        reasons = []

        if gun in (None, "disconnected", "false", "off"):
            reasons.append("gun_disconnected")

        active = self.get_state(self.mg_active_entity)
        state = "charging" if active == "on" else ("ready" if not reasons else "idle")

        return ChargerState(not reasons, state, reasons)

    # HA helpers
    def get_state(self, entity_id: Optional[str]) -> Optional[str]:
        if not entity_id:
            return None
        state_obj = self.hass.states.get(entity_id)
        if not state_obj or state_obj.state in ("unknown", "unavailable"):
            return None
        return state_obj.state

    # APPLY POWER (stub)
    async def async_apply_charging_power(self, allowed_power_w: int) -> None:
        """Stub: do nothing for now; only logs."""
        _LOGGER.info("controller: allowed_charging_power = %s W (stub)", allowed_power_w)
