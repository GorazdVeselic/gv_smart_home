import datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_change

from ..const import DOMAIN
from ..helpers.calendar import (
    is_weekend,
    is_holiday,
    get_holiday_name,
    get_next_holiday,
)

SCAN_INTERVAL = datetime.timedelta(minutes=1)



class GVSECalendarInfoSensor(SensorEntity):
    """Main calendar info sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = True

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self._attr_name = "GV SE Calendar Info"
        self._attr_unique_id = f"{entry_id}_calendar_info"

    @staticmethod
    def _today():
        """Return today's date. Patched in tests."""
        return datetime.date.today()

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        # Refresh daily at midnight
        self.async_on_remove(
            async_track_time_change(
                self.hass,
                self._handle_midnight_update,
                hour=0,
                minute=0,
                second=1,
            )
        )

    async def _handle_midnight_update(self, now: datetime.datetime):
        self.async_write_ha_state()

    @property
    def native_value(self):
        today = self._today()

        if is_holiday(today):
            return "holiday"
        if is_weekend(today):
            return "weekend"
        return "weekday"

    @property
    def extra_state_attributes(self):
        today = self._today()

        current_name = get_holiday_name(today)
        next_date, next_name = get_next_holiday(today)

        if next_date:
            days_to_next = (next_date - today).days
            next_date_str = next_date.isoformat()
        else:
            days_to_next = None
            next_date_str = None

        return {
            "is_weekend": is_weekend(today),
            "is_holiday": is_holiday(today),
            "is_work_free_day": is_weekend(today) or is_holiday(today),
            "holiday_name": current_name,
            "next_holiday_name": next_name,
            "next_holiday_date": next_date_str,
            "days_to_next_holiday": days_to_next,
            "today": today.isoformat(),
        }

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": "Calendar Info",
            "manufacturer": "Custom",
            "model": "GV Smart Home",
        }
