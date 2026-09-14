from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

_LOGGER = logging.getLogger(__name__)


class PowerSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "EV Charging Net Power"
    _attr_native_unit_of_measurement = "W"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        _LOGGER.debug("PowerSensor initialized")

    @property
    def native_value(self):
        # TODO: business logic
        # - read latest power from coordinator.data
        return self.coordinator.data
