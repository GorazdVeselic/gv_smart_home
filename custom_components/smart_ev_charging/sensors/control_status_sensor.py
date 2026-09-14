from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

_LOGGER = logging.getLogger(__name__)


class ControlStatusSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "EV Charging Control Status"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        _LOGGER.debug("ControlStatusSensor initialized")

    @property
    def native_value(self):
        # TODO: return something meaningful later
        # for now just prove coordinator is alive
        return "active"
