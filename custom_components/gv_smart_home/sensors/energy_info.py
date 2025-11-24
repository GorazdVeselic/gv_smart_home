import datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import DOMAIN
from ..helpers.energy import (
    is_high_season,
    get_base_block,
    get_current_block,
    get_prev_next_block_info,
    get_blocks_for_today,
)
from ..helpers.calendar import is_weekend, is_holiday


SCAN_INTERVAL_MINUTES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    """Register the GV Smart Home Energy Info sensor."""
    sensor = GVSEnergyInfoSensor(entry.entry_id)

    async_add_entities([sensor], update_before_add=True)


class GVSEnergyInfoSensor(SensorEntity):
    """Provides detailed energy tariff block information."""

    _attr_has_entity_name = True
    _attr_should_poll = True

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self._attr_name = "GV SE Energy Info"
        self._attr_unique_id = f"{entry_id}_energy_info"

    @staticmethod
    def _now() -> datetime.datetime:
        """Returns current datetime (patched during tests)."""
        return datetime.datetime.now()

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        # Midnight refresh
        self.async_on_remove(
            async_track_time_change(
                self.hass, self._handle_midnight_update,
                hour=0, minute=0, second=1
            )
        )

        # Hourly boundary refresh (block changes)
        self.async_on_remove(
            async_track_time_change(
                self.hass, self._handle_hourly_update,
                minute=0, second=1
            )
        )

    async def _handle_midnight_update(self, now: datetime.datetime):
        """Force update at midnight."""
        self.async_write_ha_state()

    async def _handle_hourly_update(self, now: datetime.datetime):
        """Force update when hour changes (block change)."""
        self.async_write_ha_state()

    #
    # MAIN VALUE
    #
    @property
    def native_value(self) -> int:
        """Return the current block as sensor value."""
        now = self._now()
        return get_current_block(now.date(), now.hour)

    #
    # ATTRIBUTES
    #
    @property
    def extra_state_attributes(self):
        now = self._now()
        today = now.date()
        hour = now.hour

        high = is_high_season(today)
        base_block = get_base_block(hour)
        effective_block = get_current_block(today, hour)
        block_info = get_prev_next_block_info(now)

        return {
            # High / Low season info
            "is_high_season": high,
            "season": "high" if high else "low",

            # Day classification
            "is_weekend": is_weekend(today),
            "is_holiday": is_holiday(today),
            "is_work_free_day": is_weekend(today) or is_holiday(today),

            # Block logic
            "effective_block": effective_block,

            # Prev / next block meta
            "previous_block": block_info["previous_block"],
            "next_block": block_info["next_block"],
            "same_as_previous": block_info["same_as_previous"],
            "same_as_next": block_info["same_as_next"],
            "minutes_since_previous": block_info["minutes_since_previous"],
            "minutes_to_next": block_info["minutes_to_next"],

            "blocks": get_blocks_for_today(today),
        }

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": "Energy Info",
            "manufacturer": "Custom",
            "model": "GV Smart Home",
        }
