from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..models.tariff_state  import TariffState

_LOGGER = logging.getLogger(__name__)


class TariffSensor(CoordinatorEntity, SensorEntity):
    """Sensor exposing the current Slovenian energy tariff block."""

    _attr_name = "EV Charging Tariff Block"
    _attr_icon = "mdi:flash"
    _attr_native_unit_of_measurement = "block"
    _attr_state_class = None  # not a measurement, just state

    def __init__(self, coordinator):
        super().__init__(coordinator)
        _LOGGER.debug("TariffSensor initialized")

    @property
    def native_value(self) -> int | None:
        """Return the current tariff block."""
        state: TariffState | None = self.coordinator.data

        if state is None:
            return None

        return state.current_block

    @property
    def extra_state_attributes(self) -> dict:
        """Expose detailed tariff context as attributes."""
        state: TariffState | None = self.coordinator.data

        if state is None:
            return {}

        return {
            # Time context
            "timestamp": state.now.isoformat(),
            "minutes_to_next_block": state.minutes_to_next,
            "minutes_since_previous_block": state.minutes_since_previous,

            # Block relations
            "previous_block": state.previous_block,
            "next_block": state.next_block,
            "same_as_previous": state.same_as_previous,
            "same_as_next": state.same_as_next,

            # Calendar context
            "is_high_season": state.is_high_season,
            "is_weekend": state.is_weekend,
            "is_holiday": state.is_holiday,
            
            "holiday_name": state.holiday_name,
            "next_holiday_date": state.next_holiday_date,
            "next_holiday_name": state.next_holiday_name,
        }
