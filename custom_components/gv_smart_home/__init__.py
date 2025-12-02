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

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """YAML setup (not used)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up GV Smart Home from a config entry."""
    _LOGGER.debug("Setting up GV Smart Home entry: %s", entry.entry_id)

    # Prepare domain storage
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(entry.entry_id, {})
    data = hass.data[DOMAIN][entry.entry_id]

    # ----------------------------------------------------------
    # 1) Create coordinator (must receive entry!)
    # ----------------------------------------------------------
    from .coordinator import GVChargingCoordinator
    coordinator = GVChargingCoordinator(hass, entry)
    data["coordinator"] = coordinator

    # ----------------------------------------------------------
    # 2) Create sampler (needs coordinator!)
    # ----------------------------------------------------------
    sampler = ConsumptionSampler(hass, entry, coordinator)
    await sampler.start()
    data["sampler"] = sampler

    # ----------------------------------------------------------
    # 3) Create charging controller (also needs coordinator!)
    # ----------------------------------------------------------
    controller = HomeChargingController(
        hass=hass,
        sampler=sampler,
        entry=entry,
        coordinator=coordinator,
    )
    controller.start()
    data["controller"] = controller

    # ----------------------------------------------------------
    # 4) Setup sensor platform(s)
    # ----------------------------------------------------------
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # ----------------------------------------------------------
    # 5) Setup live reload when options change
    # ----------------------------------------------------------
    entry.async_on_unload(
        entry.add_update_listener(async_reload_entry)
    )

    _LOGGER.debug("GV Smart Home entry initialized successfully.")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload GV Smart Home."""
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)

    if data:
        sampler = data.get("sampler")
        controller = data.get("controller")

        if sampler:
            await sampler.stop()

        if controller:
            controller.stop()

        hass.data[DOMAIN].pop(entry.entry_id, None)

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Reload when user changes configuration in UI."""
    await hass.config_entries.async_reload(entry.entry_id)
