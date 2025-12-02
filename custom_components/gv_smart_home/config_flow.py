from __future__ import annotations


from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.core import callback

from gv_smart_home.flow_schema import schema_step_blocks, schema_step_wallbox, schema_step_mg4
from .const import DOMAIN

async def async_has_unique_instance(hass: HomeAssistant) -> bool:
    """Prevent multiple copies of this integration."""
    return any(entry.domain == DOMAIN for entry in hass.config_entries.async_entries(DOMAIN))


class GVSmartHomeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for GV Smart Home."""
    VERSION = 1

    def __init__(self):
        self.values = {}

    async def async_step_user(self, user_input=None):
        if user_input:
            self.values.update(user_input)
            return await self.async_step_wallbox()

        return self.async_show_form(
            step_id="user",
            data_schema=schema_step_blocks(self.values),
        )

    async def async_step_wallbox(self, user_input=None):
        if user_input:
            self.values.update(user_input)
            return await self.async_step_mg4()

        return self.async_show_form(
            step_id="wallbox",
            data_schema=schema_step_wallbox(self.values),
        )

    async def async_step_mg4(self, user_input=None):
        if user_input:
            self.values.update(user_input)
            return self.async_create_entry(title="GV Smart Home", data=self.values)

        return self.async_show_form(
            step_id="mg4",
            data_schema=schema_step_mg4(self.values),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        from .options_flow import GVSmartHomeOptionsFlow
        return GVSmartHomeOptionsFlow(config_entry)
