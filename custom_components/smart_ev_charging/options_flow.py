from __future__ import annotations

from homeassistant import config_entries

from .flow_schema import schema_step_blocks

class SmartEvChargingOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry):
        self.entry = entry
        self.values = {**entry.data, **entry.options}

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        
        return self.async_show_form(
            step_id="init",
            data_schema=schema_step_blocks(self.values)
            )
