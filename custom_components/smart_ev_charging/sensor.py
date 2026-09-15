"""Senzorji iz spec 4.2. Ime naprave je »EV«, zato so id-ji sensor.ev_<ključ>."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import Snapshot
from .entity import SmartEvEntity


@dataclass(frozen=True)
class EvSensorDescription:
    key: str
    value: Callable[[Snapshot], Any]
    attrs: Callable[[Snapshot], dict] | None = None
    unit: str | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    precision: int | None = None


def _round(v: float | None, n: int = 2) -> float | None:
    return None if v is None else round(v, n)


SENSORS: tuple[EvSensorDescription, ...] = (
    EvSensorDescription(
        "tariff_block",
        lambda s: s.block,
        lambda s: {**s.tariff_attrs, "agreed_kw": s.agreed_kw, "reserve_kw": s.reserve_kw, "target_kw": s.target_kw},
    ),
    EvSensorDescription(
        "window_energy",
        lambda s: _round(s.window_energy_kwh, 3),
        lambda s: {
            "elapsed_min": _round(s.window_elapsed_min, 1),
            "remaining_min": _round(s.window_remaining_min, 1),
            "last_window_avg_kw": _round(s.last_window_avg_kw),
            "last_window_exceeded": s.last_window_exceeded,
        },
        unit="kWh",
        device_class=SensorDeviceClass.ENERGY,
        precision=3,
    ),
    EvSensorDescription(
        "window_projection",
        lambda s: _round(s.window_projection_kw),
        lambda s: {"p_import_kw": _round(s.p_import_kw), "p_grid_kw": _round(s.p_grid_kw), "meter_ok": s.meter_ok},
        unit="kW",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        precision=2,
    ),
    EvSensorDescription(
        "allowed_power",
        lambda s: _round(s.p_ev_allow_kw),
        lambda s: {"p_allow_kw": _round(s.p_allow_kw), "candidate": s.candidate},
        unit="kW",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        precision=2,
    ),
    EvSensorDescription(
        "other_power",
        lambda s: _round(s.p_other_used_kw),
        lambda s: {"p_ev_kw": _round(s.p_ev_kw)},
        unit="kW",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        precision=2,
    ),
    EvSensorDescription(
        "phase_headroom",
        lambda s: _round(s.i_headroom_a, 1),
        lambda s: {
            "house_a": _round(s.i_house_a[0], 1),
            "house_b": _round(s.i_house_a[1], 1),
            "house_c": _round(s.i_house_a[2], 1),
            "hard_threshold_count": s.hard_threshold_count,
        },
        unit="A",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        precision=1,
    ),
    EvSensorDescription("target_level", lambda s: s.level or "none"),
    EvSensorDescription("tier", lambda s: s.tier, lambda s: {"mode": s.mode, "wallbox_ok": s.wallbox_ok}),
    EvSensorDescription("decision_reason", lambda s: s.reason, lambda s: s.decision_inputs),
    EvSensorDescription("last_car_command", lambda s: s.last_car_command or "none", lambda s: s.last_car_command_attrs),
)


class EvSensor(SmartEvEntity, SensorEntity):
    def __init__(self, coordinator, desc: EvSensorDescription) -> None:
        super().__init__(coordinator, desc.key)
        self._desc = desc
        self._attr_native_unit_of_measurement = desc.unit
        self._attr_device_class = desc.device_class
        self._attr_state_class = desc.state_class
        if desc.precision is not None:
            self._attr_suggested_display_precision = desc.precision

    @property
    def native_value(self):
        return self._desc.value(self.snap) if self.snap else None

    @property
    def extra_state_attributes(self) -> dict | None:
        if self.snap is None or self._desc.attrs is None:
            return None
        return self._desc.attrs(self.snap)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities(EvSensor(coordinator, d) for d in SENSORS)
