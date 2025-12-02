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
    CONF_WB_POWER, CONF_WB_SET_CURRENT,
    CONF_WB_CABLE, CONF_WB_STATUS,
    CONF_MG_ACTIVE, CONF_MG_SET_CURRENT, CONF_MG_GUN_STATE,
    CC_INTERVAL_MINUTES, RAMP_DOWN_MINUTES_BEFORE,
    RAMP_UP_MAX_STEP_W, HC_WINDOW_MINUTES
)

_LOGGER = logging.getLogger(__name__)
CONTROL_INTERVAL = timedelta(minutes=CC_INTERVAL_MINUTES)


@dataclass
class ChargerState:
    available: bool
    state: str
    reasons: list[str]


class HomeChargingController:
    """EV charging logic controller (1-minute interval)."""

    def __init__(self, hass: HomeAssistant, sampler, entry: ConfigEntry, coordinator: GVChargingCoordinator):
        self.hass = hass
        self.sampler = sampler
        self.samples = sampler.samples
        self.entry = entry
        self.coordinator = coordinator

        self.last_target_power_w = 0
        self._unsub_control = None

    # ------------------------------------------------------------------
    # START/STOP
    # ------------------------------------------------------------------
    def start(self):
        self._unsub_control = async_track_time_interval(
            self.hass, self.async_control_tick, CONTROL_INTERVAL
        )
        _LOGGER.debug("HomeChargingController started")

    def stop(self):
        if self._unsub_control:
            self._unsub_control()
            self._unsub_control = None
        _LOGGER.debug("HomeChargingController stopped")

    # ------------------------------------------------------------------
    # MAIN LOOP
    # ------------------------------------------------------------------
    async def async_control_tick(self, _now):
        cfg = self.coordinator.config

        if not self.samples:
            return

        avg_grid_power_w = self.compute_average_grid_power()
        if avg_grid_power_w is None:
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

        # negative avg = import
        available_power_w = max(int(effective_limit_w + avg_grid_power_w), 0)
        target_power_w = self.apply_ramp(available_power_w)

        wb_state = self.evaluate_wallbox_state(cfg)
        mg_state = self.evaluate_mg4_state(cfg)

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
            await self.async_apply_charging_power(0)
            return

        await self.async_apply_charging_power(target_power_w)

    # ------------------------------------------------------------------
    # CALCULATIONS
    # ------------------------------------------------------------------
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

    def compute_effective_limit(self, current_limit_w, next_limit_w, minutes_to_next):
        if minutes_to_next is None:
            return current_limit_w
        if next_limit_w < current_limit_w and minutes_to_next <= RAMP_DOWN_MINUTES_BEFORE:
            return next_limit_w
        return current_limit_w

    def apply_ramp(self, new_power: int) -> int:
        old = self.last_target_power_w
        if new_power == old:
            return old
        if new_power < old:
            self.last_target_power_w = new_power
            return new_power
        ramped = min(new_power, old + RAMP_UP_MAX_STEP_W)
        self.last_target_power_w = ramped
        return ramped

    # ------------------------------------------------------------------
    # CHARGER STATE
    # ------------------------------------------------------------------
    def evaluate_wallbox_state(self, cfg) -> ChargerState:
        wb_status = cfg.get(CONF_WB_STATUS)
        wb_cable = cfg.get(CONF_WB_CABLE)

        if not wb_status and not wb_cable:
            return ChargerState(False, "unavailable", ["no_entities"])

        cable = self.get_state(cfg.get(CONF_WB_CABLE))
        status = self.get_state(cfg.get(CONF_WB_STATUS))

        reasons = []
        if cable in (None, "disconnected", "false", "off"):
            reasons.append("cable_disconnected")
        if status in ("fault", "error", None):
            if status not in ("ready", "charging"):
                reasons.append(f"status_{status}")

        state = "charging" if status == "charging" else ("ready" if not reasons else "idle")
        return ChargerState(not reasons, state, reasons)

    def evaluate_mg4_state(self, cfg) -> ChargerState:
        gun = self.get_state(cfg.get(CONF_MG_GUN_STATE))
        reasons = []
        if gun in (None, "disconnected", "false", "off"):
            reasons.append("gun_disconnected")

        active = self.get_state(cfg.get(CONF_MG_ACTIVE))
        state = "charging" if active == "on" else ("ready" if not reasons else "idle")
        return ChargerState(not reasons, state, reasons)

    # ------------------------------------------------------------------
    # HA helpers
    # ------------------------------------------------------------------
    def get_state(self, entity_id: str | None):
        if not entity_id:
            return None
        st = self.hass.states.get(entity_id)
        if not st or st.state in ("unknown", "unavailable"):
            return None
        return st.state

    async def async_apply_charging_power(self, allowed_power_w: int) -> None:
        _LOGGER.info("controller: allowed_charging_power = %s W (stub)", allowed_power_w)
