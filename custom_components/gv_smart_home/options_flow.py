from __future__ import annotations

from homeassistant import config_entries

from gv_smart_home.flow_schema import schema_step_blocks, schema_step_wallbox, schema_step_mg4

class GVSmartHomeOptionsFlow(config_entries.OptionsFlow):
    """Options flow for editing settings after installation."""

    def __init__(self, entry):
        self.entry = entry
        self.values = {**entry.data, **entry.options}

    async def async_step_init(self, user_input=None):
        if user_input:
            self.values.update(user_input)
            return await self.async_step_wallbox()

        return self.async_show_form(
            step_id="init",
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
            return self.async_create_entry(title="", data=self.values)

        return self.async_show_form(
            step_id="mg4",
            data_schema=schema_step_mg4(self.values),
        )
