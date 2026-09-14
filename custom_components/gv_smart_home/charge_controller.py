# custom_components/gv_smart_home/charge_controller.py
from __future__ import annotations
import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.config_entries import ConfigEntry

from .coordinator import GVChargingCoordinator
from .controller.house_controller import HouseController
from .controller.energy_controller import EnergyController
from .const import (
    CONF_WB_STATUS,
    CONF_WB_CABLE,
    CONF_MG_ACTIVE,
    CONF_MG_GUN_STATE,
    CC_INTERVAL_MINUTES,
    RAMP_DOWN_MINUTES_BEFORE,
    RAMP_UP_MAX_STEP_W,
)

_LOGGER = logging.getLogger(__name__)
CONTROL_INTERVAL = timedelta(minutes=CC_INTERVAL_MINUTES)


@dataclass
class ChargerState:
    available: bool
    state: str
    reasons: list[str]


class HomeChargingController:
    """
    Charging logic based on:
     - house average grid import/export
     - energy block system
     - wallbox / mg4 states
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: GVChargingCoordinator,
        house_controller: HouseController,
        energy_controller: EnergyController,
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.coordinator = coordinator

        self.house_controller = house_controller
        self.energy_controller = energy_controller

        self._unsub_control = None
        self.last_target_power_w = 0

    # ------------------------------------------------------------------
    # START/STOP
    # ------------------------------------------------------------------
    def start(self) -> None:
        self._unsub_control = async_track_time_interval(
            self.hass, self.async_control_tick, CONTROL_INTERVAL
        )
        _LOGGER.debug("HomeChargingController started")

    def stop(self) -> None:
        if self._unsub_control:
            self._unsub_control()
            self._unsub_control = None
        _LOGGER.debug("HomeChargingController stopped")

    # ------------------------------------------------------------------
    # MAIN LOOP
    # ------------------------------------------------------------------
    async def async_control_tick(self, _now) -> None:
        energy = self.energy_controller.latest
        if not energy:
            return

        latest_house = self.house_controller.get_latest_sample()
        if not latest_house:
            return

        avg_grid_power_w = self.house_controller.compute_average_grid_power()
        if avg_grid_power_w is None:
            return

        current_block   = energy["current_block"]
        next_block      = energy["next_block"]
        minutes_to_next = energy["minutes_to_next"]
        current_limit_w = energy["current_limit_w"]
        next_limit_w    = energy["next_limit_w"]

        effective_limit_w = self.compute_effective_limit(
            current_limit_w,
            next_limit_w,
            minutes_to_next,
        )

        # negative avg = import (your original semantic)
        available_power_w = max(int(effective_limit_w + avg_grid_power_w), 0)
        target_power_w = self.apply_ramp(available_power_w)

        wb_state = self.evaluate_wallbox_state(self.coordinator.config)
        mg_state = self.evaluate_mg4_state(self.coordinator.config)

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
    def compute_effective_limit(
        self,
        current_limit_w: int,
        next_limit_w: int,
        minutes_to_next: int | None,
    ) -> int:
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
    # DEVICE STATE
    # ------------------------------------------------------------------
    def evaluate_wallbox_state(self, cfg) -> ChargerState:
        status = self.get_state(cfg.get(CONF_WB_STATUS))
        cable  = self.get_state(cfg.get(CONF_WB_CABLE))

        reasons = []
        if cable in (None, "false", "off", "disconnected"):
            reasons.append("cable_disconnected")

        if status in ("fault", "error", None):
            if status not in ("ready", "charging"):
                reasons.append(f"status_{status}")

        st = "charging" if status == "charging" else ("ready" if not reasons else "idle")
        return ChargerState(not reasons, st, reasons)

    def evaluate_mg4_state(self, cfg) -> ChargerState:
        gun = self.get_state(cfg.get(CONF_MG_GUN_STATE))
        reasons = []
        if gun in (None, "false", "off", "disconnected"):
            reasons.append("gun_disconnected")

        active = self.get_state(cfg.get(CONF_MG_ACTIVE))
        st = "charging" if active == "on" else ("ready" if not reasons else "idle")
        return ChargerState(not reasons, st, reasons)

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------
    def get_state(self, entity_id: str | None) -> str | None:
        if not entity_id:
            return None
        st = self.hass.states.get(entity_id)
        if not st or st.state in ("unknown", "unavailable"):
            return None
        return st.state

    async def async_apply_charging_power(self, allowed_power_w: int) -> None:
        _LOGGER.info("controller: allowed_charging_power = %s W (stub)", allowed_power_w)
