from __future__ import annotations
from homeassistant.util import dt as dt_util


import logging
import datetime


from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from ..const import DEFAULT_TARIFF_INTERVAL
from ..models.tariff_state import TariffState

from ..helpers.energy import get_prev_next_block_info, is_high_season
from ..helpers.calendar import is_weekend, is_holiday, get_holiday_name, get_next_holiday

_LOGGER = logging.getLogger(__name__)


class TariffCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self.entry = entry

        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name="Smart EV Tariff Coordinator",
            update_interval=datetime.timedelta(seconds=DEFAULT_TARIFF_INTERVAL),
        )

    async def async_start(self) -> None:
        await self.async_config_entry_first_refresh()

    async def _async_update_data(self) -> TariffState:
        now = dt_util.now()
        #now = datetime.datetime.now(tz=self.hass.config.time_zone)

        _LOGGER.debug("TariffCoordinator tick at %s", now)

        date = now.date()

        block_info = get_prev_next_block_info(now)

        next_holiday = get_next_holiday(date)

        state = TariffState(
            now=now,

            current_block=block_info["current_block"],
            previous_block=block_info["previous_block"],
            next_block=block_info["next_block"],

            same_as_previous=block_info["same_as_previous"],
            same_as_next=block_info["same_as_next"],

            minutes_since_previous=block_info["minutes_since_previous"],
            minutes_to_next=block_info["minutes_to_next"],

            is_high_season=is_high_season(date),
            is_weekend=is_weekend(date),
            is_holiday=is_holiday(date),

            holiday_name=get_holiday_name(date),
            next_holiday_date=next_holiday[0],
            next_holiday_name=next_holiday[1]
            
        )

        _LOGGER.debug("Tariff state computed: %s", state)
        return state
