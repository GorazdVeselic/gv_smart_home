"""Smart EV Charging: polnjenje po omrežninskih blokih z rezervo in varovalko po fazah."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DEFAULT_ENTITIES
from .coordinator import SmartEvCoordinator
from .engine import Engine

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


@dataclass
class RuntimeData:
    coordinator: SmartEvCoordinator
    engine: Engine


type SmartEvConfigEntry = ConfigEntry[RuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: SmartEvConfigEntry) -> bool:
    coordinator = SmartEvCoordinator(hass, entry)
    engine = Engine(hass, entry, coordinator)
    entry.runtime_data = RuntimeData(coordinator, engine)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await engine.async_start()
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def _async_options_updated(hass: HomeAssistant, entry: SmartEvConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: SmartEvConfigEntry) -> bool:
    entry.runtime_data.engine.stop()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """v1 je imela samo moči blokov; v2 doda entitete s privzetimi produkcijskimi id-ji."""
    if entry.version == 1:
        data = {**DEFAULT_ENTITIES, **entry.data}
        data.pop("sampling_interval", None)
        hass.config_entries.async_update_entry(entry, data=data, version=2)
    return True
