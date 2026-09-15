"""Config flow: korak entitet in korak moči. Options flow ponovi oba s trenutnimi vrednostmi."""

from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN
from .flow_schema import schema_entities, schema_powers


class SmartEvChargingConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    def __init__(self) -> None:
        self._values: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if user_input is not None:
            self._values.update(user_input)
            return await self.async_step_powers()
        return self.async_show_form(step_id="user", data_schema=schema_entities(self._values))

    async def async_step_powers(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            self._values.update(user_input)
            return self.async_create_entry(title="Smart EV Charging", data=self._values)
        return self.async_show_form(step_id="powers", data_schema=schema_powers(self._values))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> SmartEvChargingOptionsFlow:
        return SmartEvChargingOptionsFlow()


class SmartEvChargingOptionsFlow(config_entries.OptionsFlow):
    def __init__(self) -> None:
        self._values: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        current = {**self.config_entry.data, **self.config_entry.options}
        if user_input is not None:
            self._values.update(user_input)
            return await self.async_step_powers()
        return self.async_show_form(step_id="init", data_schema=schema_entities(current))

    async def async_step_powers(self, user_input: dict[str, Any] | None = None):
        current = {**self.config_entry.data, **self.config_entry.options, **self._values}
        if user_input is not None:
            self._values.update(user_input)
            return self.async_create_entry(data=self._values)
        return self.async_show_form(step_id="powers", data_schema=schema_powers(current))
