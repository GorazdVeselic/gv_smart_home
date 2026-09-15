"""Sheme za config in options flow: entitete (4.1) in moči (4.2)."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.helpers import selector

from .const import (
    CONF_BLOCK_POWER,
    CONF_CABLE,
    CONF_CAR_CHARGING,
    CONF_CAR_LIMIT,
    CONF_EV_CURRENT_L1,
    CONF_EV_CURRENT_L2,
    CONF_EV_CURRENT_L3,
    CONF_EV_POWER,
    CONF_FUSE,
    CONF_FUSE_MARGIN,
    CONF_INVERT_METER,
    CONF_KW_PER_AMP,
    CONF_METER_POWER,
    CONF_METER_POWER_A,
    CONF_METER_POWER_B,
    CONF_METER_POWER_C,
    CONF_METER_VOLTAGE_A,
    CONF_METER_VOLTAGE_B,
    CONF_METER_VOLTAGE_C,
    CONF_WB_CURRENT,
    CONF_WB_ENABLE,
    CONF_WB_STATUS,
    DEFAULT_BLOCK_POWER,
    DEFAULT_ENTITIES,
    DEFAULT_FUSE,
    DEFAULT_FUSE_MARGIN,
    DEFAULT_KW_PER_AMP,
    DEFAULT_RESERVE,
    CONF_RESERVE,
)

_SENSOR = selector.EntitySelector(selector.EntitySelectorConfig(domain=["sensor", "binary_sensor", "input_number"]))
_SWITCH = selector.EntitySelector(selector.EntitySelectorConfig(domain=["switch", "input_boolean"]))
_NUMBER = selector.EntitySelector(selector.EntitySelectorConfig(domain=["number", "input_number"]))
_SELECT = selector.EntitySelector(selector.EntitySelectorConfig(domain=["select", "input_select"]))

_ENTITY_FIELDS = [
    (CONF_METER_POWER, _SENSOR),
    (CONF_METER_POWER_A, _SENSOR),
    (CONF_METER_POWER_B, _SENSOR),
    (CONF_METER_POWER_C, _SENSOR),
    (CONF_METER_VOLTAGE_A, _SENSOR),
    (CONF_METER_VOLTAGE_B, _SENSOR),
    (CONF_METER_VOLTAGE_C, _SENSOR),
    (CONF_EV_POWER, _SENSOR),
    (CONF_EV_CURRENT_L1, _SENSOR),
    (CONF_EV_CURRENT_L2, _SENSOR),
    (CONF_EV_CURRENT_L3, _SENSOR),
    (CONF_WB_STATUS, _SENSOR),
    (CONF_CABLE, _SENSOR),
    (CONF_WB_ENABLE, _SWITCH),
    (CONF_WB_CURRENT, _NUMBER),
    (CONF_CAR_LIMIT, _SELECT),
    (CONF_CAR_CHARGING, _SWITCH),
]


def _kw(default: float, maximum: float = 15.0) -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=maximum, step=0.1, unit_of_measurement="kW", mode=selector.NumberSelectorMode.BOX)
    )


def _amp(maximum: float) -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=maximum, step=1, unit_of_measurement="A", mode=selector.NumberSelectorMode.BOX)
    )


def schema_entities(values: dict) -> vol.Schema:
    fields = {
        vol.Required(key, default=values.get(key, DEFAULT_ENTITIES[key])): sel for key, sel in _ENTITY_FIELDS
    }
    fields[vol.Required(CONF_INVERT_METER, default=values.get(CONF_INVERT_METER, False))] = selector.BooleanSelector()
    return vol.Schema(fields)


def schema_powers(values: dict) -> vol.Schema:
    fields = {
        vol.Required(key, default=values.get(key, DEFAULT_BLOCK_POWER[i])): _kw(DEFAULT_BLOCK_POWER[i])
        for i, key in enumerate(CONF_BLOCK_POWER)
    }
    fields[vol.Required(CONF_RESERVE, default=values.get(CONF_RESERVE, DEFAULT_RESERVE))] = _kw(DEFAULT_RESERVE, 5.0)
    fields[vol.Required(CONF_FUSE, default=values.get(CONF_FUSE, DEFAULT_FUSE))] = _amp(63)
    fields[vol.Required(CONF_FUSE_MARGIN, default=values.get(CONF_FUSE_MARGIN, DEFAULT_FUSE_MARGIN))] = _amp(10)
    fields[vol.Required(CONF_KW_PER_AMP, default=values.get(CONF_KW_PER_AMP, DEFAULT_KW_PER_AMP))] = selector.NumberSelector(
        selector.NumberSelectorConfig(min=0.5, max=0.8, step=0.01, mode=selector.NumberSelectorMode.BOX)
    )
    return vol.Schema(fields)
