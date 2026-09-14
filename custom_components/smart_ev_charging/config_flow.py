from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN
from .flow_schema import schema_step_blocks


class SmartEvChargingConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self.values = {}

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title="Smart EV Charging",
                data=user_input,
            )


        return self.async_show_form(
            step_id="user",
            data_schema=schema_step_blocks(self.values),
            )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        from .options_flow import SmartEvChargingOptionsFlow
        return SmartEvChargingOptionsFlow(config_entry)