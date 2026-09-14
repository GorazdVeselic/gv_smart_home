# custom_components/gv_smart_home/sensors/charging_sensor.py
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

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
    """Sensor reflecting values pushed by charging controller through coordinator."""

    def __init__(
        self,
        coordinator,
        entry_id: str,
        key: str,
        name: str,
        unit: str | None,
        icon: str | None,
    ) -> None:
        super().__init__(coordinator)
        self._coordinator = coordinator

        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_should_poll = False

    @property
    def native_value(self):
        return self._coordinator.data.get(self._key)

    @property
    def available(self) -> bool:
        return self._key in self._coordinator.data

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, "gv_charging_controller")},
            "name": "GV Smart Charging",
            "manufacturer": "Gogi",
            "model": "EV Charging Logic",
        }

#@property
#def device_info(self):
#    return {
#        "identifiers": {("gv_smart_home", "charging_logic")},
#        "name": "GV Smart Charging Logic",
#        "manufacturer": "Gogi",
#        "model": "Charging Controller",
#    }
