from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

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

class GVChargingSensor(SensorEntity):
    """Sensor representing a value from the controller (via coordinator)."""

    def __init__(self, coordinator, entry_id, key, name, unit, icon):
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

    entities = [
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

    async_add_entities(entities)
