# custom_components/gv_smart_home/__init__.py
from __future__ import annotations

import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform

from .const import DOMAIN
from .coordinator import GVChargingCoordinator

# Controllers
from .house.controller import HouseController
from .house.sampler import HouseSampler
from .energy.controller import EnergyController
from .wallbox.controller import WallboxController
from .mg4.controller import MG4Controller
from .charging.controller import HomeChargingController

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]


# --------------------------------------------------------------
# YAML setup (not used)
# --------------------------------------------------------------
async def async_setup(hass: HomeAssistant, config) -> bool:
    return True


# --------------------------------------------------------------
# CONFIG FLOW ENTRY SETUP
# --------------------------------------------------------------
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Initialize GV Smart Home integration from config entry."""
    _LOGGER.info("Setting up GV Smart Home entry: %s", entry.entry_id)

    # Domain storage root
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(entry.entry_id, {})
    data = hass.data[DOMAIN][entry.entry_id]

    # ----------------------------------------------------------
    # 1) Coordinator (central storage)
    # ----------------------------------------------------------
    coordinator = GVChargingCoordinator(hass, entry)
    data["coordinator"] = coordinator

    # ----------------------------------------------------------
    # 2) HouseController + HouseSampler
    # ----------------------------------------------------------
    house_controller = HouseController()
    sampler = HouseSampler(
        hass=hass,
        entry=entry,
        coordinator=coordinator,
        house_controller=house_controller,
    )
    data["house_controller"] = house_controller
    data["sampler"] = sampler

    # ----------------------------------------------------------
    # 3) EnergyController
    # ----------------------------------------------------------
    energy = EnergyController(hass=hass, coordinator=coordinator)
    data["energy"] = energy

    # ----------------------------------------------------------
    # 4) WallboxController
    # ----------------------------------------------------------
    wallbox = WallboxController(
        hass=hass,
        entry=entry,
        coordinator=coordinator,
    )
    data["wallbox"] = wallbox

    # ----------------------------------------------------------
    # 5) MG4Controller
    # ----------------------------------------------------------
    mg4 = MG4Controller(
        hass=hass,
        coordinator=coordinator,
    )
    data["mg4"] = mg4

    # ----------------------------------------------------------
    # 6) ChargingController (main logic)
    # ----------------------------------------------------------
    charging = HomeChargingController(
        hass=hass,
        sampler=house_controller,
        energy=energy,
        wallbox=wallbox,
        mg4=mg4,
        coordinator=coordinator,
    )
    data["charging"] = charging

    # ----------------------------------------------------------
    # 7) Start modules in correct order
    # ----------------------------------------------------------
    await sampler.start()     # starts grid sampling
    await energy.start()      # midnight + hourly events
    charging.start()          # main 1-min charging loop

    # First-run updates for modules without timers
    await wallbox.update()
    await mg4.update()

    # ----------------------------------------------------------
    # 8) Register platforms (sensors)
    # ----------------------------------------------------------
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload when options change
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    _LOGGER.info("GV Smart Home setup complete")
    return True


# --------------------------------------------------------------
# ENTRY UNLOAD
# --------------------------------------------------------------
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload integration resources."""
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if not data:
        return True

    sampler = data.get("sampler")
    energy = data.get("energy")
    charging = data.get("charging")

    if sampler:
        await sampler.stop()
    if energy:
        await energy.stop()
    if charging:
        await charging.stop()

    hass.data[DOMAIN].pop(entry.entry_id, None)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


# --------------------------------------------------------------
# RELOAD ENTRY
# --------------------------------------------------------------
async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)
