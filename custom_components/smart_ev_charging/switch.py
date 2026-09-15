"""Stikalo »polni v vsakem primeru« (spec 4.2, 6.4 korak 6). Obnovi se po zagonu."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .entity import SmartEvEntity


class EvChargeAnywaySwitch(SmartEvEntity, SwitchEntity, RestoreEntity):
    def __init__(self, coordinator, engine) -> None:
        super().__init__(coordinator, "charge_anyway", "switch")
        self._engine = engine
        self._attr_is_on = False

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state in ("on", "off"):
            self._attr_is_on = last.state == "on"
        self._engine.set_charge_anyway(bool(self._attr_is_on))

    async def async_turn_on(self, **kwargs) -> None:
        self._attr_is_on = True
        self._engine.set_charge_anyway(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self._attr_is_on = False
        self._engine.set_charge_anyway(False)
        self.async_write_ha_state()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    rt = entry.runtime_data
    async_add_entities([EvChargeAnywaySwitch(rt.coordinator, rt.engine)])
