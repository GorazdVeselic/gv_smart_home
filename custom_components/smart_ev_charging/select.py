"""Način regulatorja (spec 1 in 4.2): off, observe, tariff. Obnovi se po zagonu."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import MODES
from .entity import SmartEvEntity


class EvModeSelect(SmartEvEntity, SelectEntity, RestoreEntity):
    _attr_options = list(MODES)

    def __init__(self, coordinator, engine) -> None:
        super().__init__(coordinator, "mode", "select")
        self._engine = engine
        self._attr_current_option = engine.mode

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state in MODES:
            self._attr_current_option = last.state
        self._engine.set_mode(self._attr_current_option)

    async def async_select_option(self, option: str) -> None:
        self._attr_current_option = option
        self._engine.set_mode(option)
        self.async_write_ha_state()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    rt = entry.runtime_data
    async_add_entities([EvModeSelect(rt.coordinator, rt.engine)])
