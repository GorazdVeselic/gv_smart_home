from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator.sampling_coordinator import SamplingCoordinator
from .coordinator.control_coordinator import ControlCoordinator
from .coordinator.tariff_coordinator import TariffCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.info("Initializing Smart EV Charging integration")

    hass.data.setdefault(DOMAIN, {})

    sampling = SamplingCoordinator(hass, entry)
    control = ControlCoordinator(hass, entry)
    tariff = TariffCoordinator(hass, entry)

    hass.data[DOMAIN][entry.entry_id] = {
        "sampling": sampling,
        "control": control,
        "tariff": tariff,
    }

    _LOGGER.debug("Starting coordinators (first refresh)")
    await sampling.async_start()
    await control.async_start()
    await tariff.async_start()

    _LOGGER.debug("Forwarding sensor platform setup")
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    _LOGGER.info("Smart EV Charging initialized")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.info("Unloading Smart EV Charging integration")

    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok
