from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from ..const import DOMAIN

SENSORS = [
    ("avg_grid_power_w", "GV Avg Grid Power", "W", "mdi:flash"),
    ("effective_limit_w", "GV Effective Limit", "W", "mdi:flash-outline"),
    ("available_power_w", "GV Available Power", "W", "mdi:ev-station"),
    ("target_power_w", "GV Target EV Power", "W", "mdi:ev-plug-type2"),
    ("current_block", "GV Current Block", None, "mdi:calendar-clock"),
    ("next_block", "GV Next Block", None, "mdi:calendar-arrow-right"),
    ("minutes_to_next", "GV Minutes To Next Block", "min", "mdi:timer-outline"),
]


class GVChargingSensor(CoordinatorEntity, SensorEntity):
    """Sensor that exposes values from the charging controller."""

    def __init__(self, coordinator, entry_id, key, name, unit, icon):
        super().__init__(coordinator)
        self._attr_should_poll = False
        self._coordinator = coordinator
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon

    @property
    def native_value(self):
        return self._coordinator.data.get(self._key)

    @property
    def available(self):
        # available if we've received at least one update for this key
        return self._key in self._coordinator.data

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, "gv_charging_controller")},
            "name": "GV Smart Charging",
            "manufacturer": "Gogi",
            "model": "EV Charging Logic",
        }


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    # Create one entity per sensor metric
    sensors = [
        GVChargingSensor(
            coordinator,
            entry.entry_id,
            key,
            name,
            unit,
            icon,
        )
        for (key, name, unit, icon) in SENSORS
    ]

    async_add_entities(sensors)
