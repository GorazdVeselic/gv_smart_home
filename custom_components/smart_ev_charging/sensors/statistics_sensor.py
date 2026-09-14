from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

_LOGGER = logging.getLogger(__name__)


class StatisticsSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "EV Charging 15min Average Power"
    _attr_native_unit_of_measurement = "W"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        _LOGGER.debug("StatisticsSensor initialized")

    @property
    def native_value(self):
        # TODO: business logic
        # - compute rolling 15min average from sample buffer
        return None
