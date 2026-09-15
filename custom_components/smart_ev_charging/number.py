"""Nastavitve iz spec 4.2 kot number entitete z obnovitvijo stanja.

Začetna vrednost pride iz config vnosa, potem velja zadnja vrednost iz UI.
Sprememba gre takoj v Engine.update_config, zgodovina regulatorja ostane.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberMode, RestoreNumber
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_BLOCK_POWER,
    CONF_FUSE,
    CONF_FUSE_MARGIN,
    CONF_RESERVE,
    DEFAULT_BLOCK_POWER,
    DEFAULT_FUSE,
    DEFAULT_FUSE_MARGIN,
    DEFAULT_RESERVE,
)
from .entity import SmartEvEntity


@dataclass(frozen=True)
class EvNumberDescription:
    key: str
    conf: str
    default: float
    unit: str
    minimum: float
    maximum: float
    step: float


NUMBERS: tuple[EvNumberDescription, ...] = tuple(
    EvNumberDescription(f"block_{i + 1}_power", conf, DEFAULT_BLOCK_POWER[i], "kW", 0.0, 15.0, 0.1)
    for i, conf in enumerate(CONF_BLOCK_POWER)
) + (
    EvNumberDescription("reserve_power", CONF_RESERVE, DEFAULT_RESERVE, "kW", 0.0, 5.0, 0.1),
    EvNumberDescription("fuse_current", CONF_FUSE, DEFAULT_FUSE, "A", 6.0, 63.0, 1.0),
    EvNumberDescription("fuse_margin", CONF_FUSE_MARGIN, DEFAULT_FUSE_MARGIN, "A", 0.0, 10.0, 1.0),
)


class EvNumber(SmartEvEntity, RestoreNumber):
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, engine, desc: EvNumberDescription) -> None:
        super().__init__(coordinator, desc.key, "number")
        self._engine = engine
        self._desc = desc
        self._attr_native_unit_of_measurement = desc.unit
        self._attr_native_min_value = desc.minimum
        self._attr_native_max_value = desc.maximum
        self._attr_native_step = desc.step
        self._attr_native_value = float(engine.cfg_values.get(desc.conf, desc.default))

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        if last is not None and last.native_value is not None:
            self._attr_native_value = float(last.native_value)
        self._engine.update_config(**{self._desc.conf: self._attr_native_value})

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self._engine.update_config(**{self._desc.conf: value})
        self.async_write_ha_state()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    rt = entry.runtime_data
    async_add_entities(EvNumber(rt.coordinator, rt.engine, d) for d in NUMBERS)
