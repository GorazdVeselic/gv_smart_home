import datetime

from core.calendar import (
    calculate_easter_date,
    get_holiday_name,
    get_next_holiday,
    is_holiday,
    is_weekday,
    is_weekend,
)


def test_is_weekday_and_weekend():
    assert is_weekday(datetime.date(2025, 1, 6))  # ponedeljek
    assert not is_weekday(datetime.date(2025, 1, 5))  # nedelja
    assert is_weekend(datetime.date(2025, 1, 5))
    assert not is_weekend(datetime.date(2025, 1, 6))


def test_calculate_easter_date_known_values():
    assert calculate_easter_date(2025) == datetime.date(2025, 4, 20)
    assert calculate_easter_date(2024) == datetime.date(2024, 3, 31)
    assert calculate_easter_date(2026) == datetime.date(2026, 4, 5)


def test_is_holiday_positive_and_negative():
    assert is_holiday(datetime.date(2025, 1, 1))
    assert is_holiday(datetime.date(2026, 4, 6))  # velikonočni ponedeljek
    assert not is_holiday(datetime.date(2025, 1, 3))


def test_get_holiday_name():
    assert get_holiday_name(datetime.date(2025, 1, 1)) == "Novo leto"
    assert get_holiday_name(datetime.date(2025, 7, 3)) is None


def test_get_next_holiday_crosses_year():
    next_date, next_name = get_next_holiday(datetime.date(2025, 1, 1))
    assert next_date == datetime.date(2025, 1, 2)
    assert next_name == "Novo leto (2. dan)"
    next_date2, next_name2 = get_next_holiday(datetime.date(2025, 12, 31))
    assert next_date2 == datetime.date(2026, 1, 1)
    assert next_name2 == "Novo leto"
