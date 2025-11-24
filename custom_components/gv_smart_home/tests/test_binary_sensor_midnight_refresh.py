import datetime
import pytest
from unittest.mock import patch

from custom_components.gv_smart_home.sensor.calendar_info import (
    GVSECalendarInfoSensor,
)


async def test_midnight_refresh_triggers_state_update():
    """Verify that the calendar info sensor refreshes at midnight."""

    # ---- 1) Init sensor ----
    sensor = GVSECalendarInfoSensor("test_entry")

    # ---- 2) Capture async_write_ha_state calls ----
    state_updates = {"called": False}

    def fake_write_state():
        state_updates["called"] = True

    sensor.async_write_ha_state = fake_write_state

    # ---- 3) Intercept async_track_time_change ----
    registered_callbacks = []

    def fake_track_time_change(hass, callback, **kwargs):
        registered_callbacks.append(callback)
        # simulate returning "remove" unregister function
        return lambda: None

    # ---- 4) Patch correct import-path of async_track_time_change ----
    with patch(
        "custom_components.gv_smart_home.sensor.calendar_info.async_track_time_change",
        new=fake_track_time_change,
    ):
        await sensor.async_added_to_hass()

    # ---- 5) Ensure the midnight callback was registered ----
    assert len(registered_callbacks) == 1
    midnight_callback = registered_callbacks[0]

    # ---- 6) Simulate midnight ----
    fake_now = datetime.datetime(2025, 1, 1, 0, 0, 1)

    await midnight_callback(fake_now)

    # ---- 7) Verify state refresh was triggered ----
    assert state_updates["called"] is True
