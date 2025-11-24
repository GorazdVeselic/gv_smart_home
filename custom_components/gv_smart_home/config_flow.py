from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import *


async def async_has_unique_instance(hass: HomeAssistant) -> bool:
    """Prevent multiple copies of this integration."""
    return any(entry.domain == DOMAIN for entry in hass.config_entries.async_entries(DOMAIN))


class GVSmartHomeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for GV Smart Home."""

    VERSION = 1

    def __init__(self):
        self.data: dict[str, Any] = {}

    # -------------------------------------------------------------------------
    # STEP 1 — BLOCK POWERS + HOUSE CONSUMPTION
    # -------------------------------------------------------------------------
    async def async_step_user(
            self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:

        if await async_has_unique_instance(self.hass):
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_wallbox()

        schema = vol.Schema(
            {
                vol.Required(CONF_BLOCK_1, default=5.0): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=13,
                        step=0.1,
                        unit_of_measurement="kW",
                        mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Required(CONF_BLOCK_2, default=5.0): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=13,
                        step=0.1,
                        unit_of_measurement="kW",
                        mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Required(CONF_BLOCK_3, default=5.0): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=13,
                        step=0.1,
                        unit_of_measurement="kW",
                        mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Required(CONF_BLOCK_4, default=5.0): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=13,
                        step=0.1,
                        unit_of_measurement="kW",
                        mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Required(CONF_BLOCK_5, default=5.0): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=13,
                        step=0.1,
                        unit_of_measurement="kW",
                        mode=selector.NumberSelectorMode.BOX
                    )
                ),

                vol.Required(CONF_GRID_POWER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor"])
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            description_placeholders={},
        )

    # -------------------------------------------------------------------------
    # STEP 2 — WALLBOX
    # -------------------------------------------------------------------------
    async def async_step_wallbox(
            self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:

        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_mg4()

        schema = vol.Schema(
            {
                vol.Required(CONF_WB_ACTIVE): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["switch"])
                ),
                vol.Required(CONF_WB_POWER): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor"])
                ),
                vol.Required(CONF_WB_SET_CURRENT): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["number"])
                ),
                vol.Required(CONF_WB_CABLE): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["binary_sensor"])
                ),
                vol.Required(CONF_WB_STATUS): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor"])
                ),
            }
        )

        return self.async_show_form(
            step_id="wallbox",
            data_schema=schema,
        )

    # -------------------------------------------------------------------------
    # STEP 3 — MG4
    # -------------------------------------------------------------------------
    async def async_step_mg4(
            self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:

        if user_input is not None:
            self.data.update(user_input)
            return self.async_create_entry(
                title="GV Smart Home",
                data=self.data,
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_MG_ACTIVE): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["switch"])
                ),
                vol.Required(CONF_MG_GUN_STATE): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["binary_sensor"])
                ),
                vol.Required(CONF_MG_SET_CURRENT): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["select", "number"])
                ),
            }
        )

        return self.async_show_form(
            step_id="mg4",
            data_schema=schema,
        )
