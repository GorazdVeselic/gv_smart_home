from homeassistant.components.sensor import SensorEntity

from .const import DOMAIN
from .sensors.calendar_info import GVSECalendarInfoSensor
from .sensors.charging_sensor import GVChargingSensor, SENSORS  # SENSORS = lista definicij
from .sensors.energy_info import GVSEnergyInfoSensor


async def async_setup_entry(
        hass,
        entry,
        async_add_entities
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    sensors = [
        GVSECalendarInfoSensor(entry.entry_id),
        GVSEnergyInfoSensor(entry.entry_id),
    ]

    # Add all charging sensors (factory pattern)
    for key, name, unit, icon in SENSORS:
        sensors.append(
            GVChargingSensor(
                coordinator=coordinator,
                entry_id=entry.entry_id,
                key=key,
                name=name,
                unit=unit,
                icon=icon,
            )
        )

    async_add_entities(sensors, update_before_add=True)

