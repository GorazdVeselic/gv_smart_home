import datetime
import pytest

from custom_components.gv_smart_home.helpers import (
    is_weekday,
    is_weekend,
    calculate_easter_date,
    is_holiday,
    get_holiday_name,
    get_next_holiday,
)


def test_is_weekday_and_weekend():
    assert is_weekday(datetime.date(2025, 1, 6))  # Monday
    assert not is_weekday(datetime.date(2025, 1, 5))  # Sunday

    assert is_weekend(datetime.date(2025, 1, 5))  # Sunday
    assert not is_weekend(datetime.date(2025, 1, 6))  # Monday


def test_calculate_easter_date_known_values():
    # Znan datum za veliko noč:
    # 2025: 20. april
    assert calculate_easter_date(2025) == datetime.date(2025, 4, 20)

    # 2024: 31. marec
    assert calculate_easter_date(2024) == datetime.date(2024, 3, 31)


def test_is_holiday_positive_and_negative():
    assert is_holiday(datetime.date(2025, 1, 1))  # Novo leto
    assert not is_holiday(datetime.date(2025, 1, 3))  # navaden dan


def test_get_holiday_name():
    assert get_holiday_name(datetime.date(2025, 1, 1)) == "Novo leto"
    assert get_holiday_name(datetime.date(2025, 7, 3)) is None


def test_get_next_holiday():
    next_date, next_name = get_next_holiday(datetime.date(2025, 1, 1))
    assert next_date > datetime.date(2025, 1, 1)
    assert next_name is not None

    # Zadnji dan v letu → preseči v naslednje leto
    next_date2, next_name2 = get_next_holiday(datetime.date(2025, 12, 31))
    assert isinstance(next_date2, datetime.date)
    assert isinstance(next_name2, str)
