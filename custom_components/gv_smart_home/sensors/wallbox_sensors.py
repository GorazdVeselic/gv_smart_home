# custom_components/gv_smart_home/sensors/wallbox_sensors.py
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity


class WallboxBaseSensor(CoordinatorEntity, SensorEntity):
    """Shared base for Wallbox sensors."""
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
            "identifiers": {("gv_smart_home", "wallbox")},
            "name": "GV Wallbox",
            "manufacturer": "Gogi",
            "model": "Wallbox State Evaluator",
        }


class WallboxAvailableSensor(WallboxBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "wb_available", "GV WB Available", "gv_wb_available")


class WallboxStateSensor(WallboxBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "wb_state", "GV WB State", "gv_wb_state")


class WallboxCableSensor(WallboxBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "wb_cable_connected", "GV WB Cable Connected", "gv_wb_cable")


class WallboxStatusRawSensor(WallboxBaseSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "wb_status_raw", "GV WB Status Raw", "gv_wb_status_raw")
