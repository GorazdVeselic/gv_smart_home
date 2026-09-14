# custom_components/gv_smart_home/sensors/energy_sensors.py
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity


# ============================================================
# CURRENT BLOCK
# ============================================================
class EnergyCurrentBlockSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "GV Energy Current Block"
    _attr_should_poll = False

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = "gv_energy_current_block"

    @property
    def native_value(self):
        return self.coordinator.data.get("current_block")

    @property
    def device_info(self):
        return {
            "identifiers": {("gv_smart_home", "core")},
            "name": "GV Smart Home",
            "manufacturer": "Gogi",
            "model": "Core Energy Logic",
        }


# ============================================================
# NEXT BLOCK
# ============================================================
class EnergyNextBlockSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "GV Energy Next Block"
    _attr_should_poll = False

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = "gv_energy_next_block"

    @property
    def native_value(self):
        return self.coordinator.data.get("next_block")

    @property
    def device_info(self):
        return {
            "identifiers": {("gv_smart_home", "core")},
            "name": "GV Smart Home",
            "manufacturer": "Gogi",
            "model": "Core Energy Logic",
        }


# ============================================================
# MINUTES TO NEXT BLOCK
# ============================================================
class EnergyMinutesToNextSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "GV Energy Minutes To Next Block"
    _attr_should_poll = False

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = "gv_energy_minutes_next"

    @property
    def native_value(self):
        return self.coordinator.data.get("minutes_to_next")

    @property
    def device_info(self):
        return {
            "identifiers": {("gv_smart_home", "core")},
            "name": "GV Smart Home",
            "manufacturer": "Gogi",
            "model": "Core Energy Logic",
        }


# ============================================================
# SEASON SENSOR
# ============================================================
class EnergySeasonSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "GV Energy Season"
    _attr_should_poll = False

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = "gv_energy_season"

    @property
    def native_value(self):
        return self.coordinator.data.get("season")

    @property
    def device_info(self):
        return {
            "identifiers": {("gv_smart_home", "core")},
            "name": "GV Smart Home",
            "manufacturer": "Gogi",
            "model": "Core Energy Logic",
        }
