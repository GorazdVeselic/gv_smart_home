# custom_components/gv_smart_home/sensor.py
from __future__ import annotations

import logging
from typing import Any, List

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

# Correct imports based on your actual file names + class names
from .sensors.calendar_sensors import GVCalendarInfoSensor

from .sensors.energy_sensors import (
    EnergyCurrentBlockSensor,
    EnergyNextBlockSensor,
    EnergyMinutesToNextSensor,
    EnergySeasonSensor,
)

from .sensors.charging_sensor import GVChargingSensor, SENSORS

from .sensors.wallbox_sensors import (
    WallboxAvailableSensor,
    WallboxStateSensor,
    WallboxCableSensor,
    WallboxStatusRawSensor,
)

from .sensors.mg4_sensors import (
    MG4AvailableSensor,
    MG4StateSensor,
    MG4GunSensor,
    MG4ChargingActiveSensor,
    MG4CurrentLimitSensor,
    MG4CurrentRawSensor,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Register all GV Smart Home sensors."""

    data: dict[str, Any] = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    entities: List[Any] = []

    #
    # CALENDAR SENSOR
    #
    entities.append(GVCalendarInfoSensor(coordinator))

    #
    # ENERGY SENSORS
    #
    entities.append(EnergyCurrentBlockSensor(coordinator))
    entities.append(EnergyNextBlockSensor(coordinator))
    entities.append(EnergyMinutesToNextSensor(coordinator))
    entities.append(EnergySeasonSensor(coordinator))

    #
    # WALLBOX SENSORS
    #
    entities.append(WallboxAvailableSensor(coordinator))
    entities.append(WallboxStateSensor(coordinator))
    entities.append(WallboxCableSensor(coordinator))
    entities.append(WallboxStatusRawSensor(coordinator))

    #
    # MG4 SENSORS
    #
    entities.append(MG4AvailableSensor(coordinator))
    entities.append(MG4StateSensor(coordinator))
    entities.append(MG4GunSensor(coordinator))
    entities.append(MG4ChargingActiveSensor(coordinator))
    entities.append(MG4CurrentLimitSensor(coordinator))
    entities.append(MG4CurrentRawSensor(coordinator))


    #
    # CHARGING SENSORS (dynamic) driven by coordinator.data
    #
    for key, name, unit, icon in SENSORS:
        entities.append(
            GVChargingSensor(
                coordinator=coordinator,
                entry_id=entry.entry_id,
                key=key,
                name=name,
                unit=unit,
                icon=icon,
            )
        )

    _LOGGER.debug(
        "GV Smart Home: adding %s sensor entities for %s",
        len(entities),
        entry.entry_id,
    )

    async_add_entities(entities, update_before_add=True)
