from homeassistant.helpers import selector
import voluptuous as vol

from gv_smart_home.const import *


def schema_step_blocks(values: dict):
    return vol.Schema({
        vol.Required(
            CONF_BLOCK_1,
            default=values.get(CONF_BLOCK_1, 5.0)
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=13, step=0.1,
                unit_of_measurement="kW",
                mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Required(
            CONF_BLOCK_2,
            default=values.get(CONF_BLOCK_2, 5.0)
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=13, step=0.1,
                unit_of_measurement="kW",
                mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Required(
            CONF_BLOCK_3,
            default=values.get(CONF_BLOCK_3, 5.0)
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=13, step=0.1,
                unit_of_measurement="kW",
                mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Required(
            CONF_BLOCK_4,
            default=values.get(CONF_BLOCK_4, 5.0)
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=13, step=0.1,
                unit_of_measurement="kW",
                mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Required(
            CONF_BLOCK_5,
            default=values.get(CONF_BLOCK_5, 5.0)
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=13, step=0.1,
                unit_of_measurement="kW",
                mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Required(
            CONF_GRID_POWER_ENTITY,
            default=values.get(CONF_GRID_POWER_ENTITY)
        ): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["sensor"],
                device_class="power",
            )
        )
    })


def schema_step_wallbox(values: dict):
    return vol.Schema({
        vol.Required(
            CONF_WB_POWER,
            default=values.get(CONF_WB_POWER)

        ): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["sensor"],
                device_class="power"
            )
        ),
        vol.Required(
            CONF_WB_SET_CURRENT,
            default=values.get(CONF_WB_SET_CURRENT)
        ): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["number"],
            )
        ),
        vol.Required(
            CONF_WB_CABLE,
            default=values.get(CONF_WB_CABLE)
        ): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["binary_sensor"],
            )
        ),
        vol.Required(
            CONF_WB_STATUS,
            default=values.get(CONF_WB_STATUS)
        ): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor"])
        ),
    })


def schema_step_mg4(values: dict):
    return vol.Schema({
        vol.Required(
            CONF_MG_ACTIVE,
            default=values.get(CONF_MG_ACTIVE)
        ): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["switch"])
        ),
        vol.Required(
            CONF_MG_GUN_STATE,
            default=values.get(CONF_MG_GUN_STATE)
        ): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["binary_sensor"])
        ),
        vol.Required(
            CONF_MG_SET_CURRENT,
            default=values.get(CONF_MG_SET_CURRENT)
        ): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["select", "number"])
        ),
    })
