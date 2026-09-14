from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity


class GVCalendarInfoSensor(CoordinatorEntity, SensorEntity):
    """Calendar + work-free sensor (driven by EnergyCoordinator)."""

    _attr_name = "GV Calendar Info"
    _attr_should_poll = False

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = "gv_calendar_info"

    @property
    def native_value(self):
        """weekday / weekend / holiday"""
        if self.coordinator.data.get("is_holiday"):
            return "holiday"
        if self.coordinator.data.get("is_weekend"):
            return "weekend"
        return "weekday"

    @property
    def extra_state_attributes(self):
        return {
            "is_weekend": self.coordinator.data.get("is_weekend"),
            "is_holiday": self.coordinator.data.get("is_holiday"),
            "is_work_free_day": self.coordinator.data.get("is_work_free_day"),
            "holiday_name": self.coordinator.data.get("holiday_name"),
            "next_holiday_name": self.coordinator.data.get("next_holiday_name"),
            "next_holiday_date": self.coordinator.data.get("next_holiday_date"),
        }

    @property
    def device_info(self):
        return {
            "identifiers": {("gv_smart_home", "core")},
            "name": "GV Smart Home",
            "manufacturer": "Gogi",
            "model": "Core Logic",
        }