from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .consumption_sampler import ConsumptionSampler
from .charge_controller import HomeChargingController

_LOGGER = logging.getLogger(__name__)

# Register platforms
PLATFORMS: list[Platform] = [
    Platform.SENSOR,
]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """YAML setup (not used)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up GV Smart Home from a config entry."""

    _LOGGER.debug("Setting up GV Smart Home entry: %s", entry.entry_id)

    # Ensure main domain dict exists
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(entry.entry_id, {})
    data = hass.data[DOMAIN][entry.entry_id]

    # 1) Create coordinator
    from .coordinator import GVChargingCoordinator
    coordinator = GVChargingCoordinator(hass)
    data["coordinator"] = coordinator

    # 2) Start sampler (1s)
    sampler = ConsumptionSampler(hass, entry)
    await sampler.start()
    data["sampler"] = sampler

    # 3) Start charging controller 1m
    controller = HomeChargingController(
        hass=hass,
        sampler=sampler,
        config_entry=entry,
        coordinator=coordinator,
    )
    controller.start()
    data["controller"] = controller

    # 4) Load entity platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.debug("GV Smart Home entry initialized successfully.")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)

    if data:
        sampler = data.get("sampler")
        controller = data.get("controller")

        if sampler:
            sampler.stop()

        if controller:
            controller.stop()

        hass.data[DOMAIN].pop(entry.entry_id, None)

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
