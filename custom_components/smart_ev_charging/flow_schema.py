from homeassistant.helpers import selector
import voluptuous as vol

from .const import (
    CONF_SAMPLING_INTERVAL,
    DEFAULT_SAMPLING_INTERVAL,
    CONF_BLOCK_1,
    CONF_BLOCK_2,
    CONF_BLOCK_3,
    CONF_BLOCK_4,
    CONF_BLOCK_5,
)

def schema_step_blocks(values: dict):
    return vol.Schema({
        vol.Optional(
            CONF_SAMPLING_INTERVAL,
            default=DEFAULT_SAMPLING_INTERVAL,
        ): vol.Coerce(int),
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
        )
    })

