# custom_components/gv_smart_home/sensors/mg4_sensors.py
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity


class MG4BaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for all MG4 sensors."""

    _attr_should_poll = False

    def __init__(self, coordinator, key: str, name: str, unique_id: str):
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_unique_id = unique_id

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key)

    @property
    def available(self):
        return self._key in self.coordinator.data

    @property
    def device_info(self):
        return {
            "identifiers": {("gv_smart_home", "mg4")},
            "name": "MG4 EV",
            "manufacturer": "Gogi",
            "model": "MG4 Charging Logic",
        }


class MG4AvailableSensor(MG4BaseSensor):
    def __init__(self, c):
        super().__init__(c, "mg_available", "GV MG4 Available", "gv_mg4_available")


class MG4StateSensor(MG4BaseSensor):
    def __init__(self, c):
        super().__init__(c, "mg_state", "GV MG4 State", "gv_mg4_state")


class MG4GunSensor(MG4BaseSensor):
    def __init__(self, c):
        super().__init__(c, "mg_gun_connected", "GV MG4 Gun Connected", "gv_mg4_gun")


class MG4ChargingActiveSensor(MG4BaseSensor):
    def __init__(self, c):
        super().__init__(c, "mg_charging_active", "GV MG4 Charging Active", "gv_mg4_active")


class MG4CurrentLimitSensor(MG4BaseSensor):
    def __init__(self, c):
        super().__init__(c, "mg_current_limit", "GV MG4 Current Limit (A)", "gv_mg4_limit")


class MG4CurrentRawSensor(MG4BaseSensor):
    def __init__(self, c):
        super().__init__(c, "mg_set_current_raw", "GV MG4 Current Raw", "gv_mg4_raw")
