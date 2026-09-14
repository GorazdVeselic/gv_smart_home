from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .sensors.power_sensor import PowerSensor
from .sensors.tariff_sensor import TariffSensor
from .sensors.statistics_sensor import StatisticsSensor
from .sensors.control_status_sensor import ControlStatusSensor


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    _LOGGER.info("Setting up Smart EV Charging sensors")

    data = hass.data[DOMAIN][entry.entry_id]
    sampling = data["sampling"]
    control = data["control"]
    tariff = data["tariff"]

    async_add_entities([
        PowerSensor(sampling),
        StatisticsSensor(sampling),
        TariffSensor(tariff),
        ControlStatusSensor(control),
    ])
