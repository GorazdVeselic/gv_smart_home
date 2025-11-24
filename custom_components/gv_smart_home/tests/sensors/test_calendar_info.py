import datetime
import pytest

from custom_components.gv_smart_home.sensor.calendar_info import GVSECalendarInfoSensor
from custom_components.gv_smart_home.helpers import calendar as cal_module
from custom_components.gv_smart_home.sensor import calendar_info as info_module


def test_calendar_info_weekday(monkeypatch):
    monkeypatch.setattr(
        GVSECalendarInfoSensor,
        "_today",
        staticmethod(lambda: datetime.date(2024, 5, 8))
    )

    monkeypatch.setattr(cal_module, "is_weekend", lambda d: False)
    monkeypatch.setattr(cal_module, "is_holiday", lambda d: False)

    sensor = GVSECalendarInfoSensor("test_entry")

    assert sensor.native_value == "weekday"


def test_calendar_info_holiday(monkeypatch):
    monkeypatch.setattr(
        GVSECalendarInfoSensor,
        "_today",
        staticmethod(lambda: datetime.date(2024, 12, 25))
    )

    monkeypatch.setattr(cal_module, "is_holiday", lambda d: True)
    monkeypatch.setattr(cal_module, "is_weekend", lambda d: False)

    sensor = GVSECalendarInfoSensor("test_entry")

    assert sensor.native_value == "holiday"


def test_calendar_info_attributes(monkeypatch):
    today = datetime.date(2024, 5, 8)

    monkeypatch.setattr(
        GVSECalendarInfoSensor,
        "_today",
        staticmethod(lambda: today)
    )

    monkeypatch.setattr(info_module, "is_weekend", lambda d: False)
    monkeypatch.setattr(info_module, "is_holiday", lambda d: True)
    monkeypatch.setattr(info_module, "get_holiday_name", lambda d: "TestHoliday")
    monkeypatch.setattr(
        info_module,
        "get_next_holiday",
        lambda d: (datetime.date(2024, 12, 25), "Christmas"),
    )

    sensor = GVSECalendarInfoSensor("test_entry")

    attrs = sensor.extra_state_attributes

    assert attrs["holiday_name"] == "TestHoliday"
    assert attrs["next_holiday_name"] == "Christmas"
    assert attrs["is_holiday"] is True
    assert attrs["is_weekend"] is False
