import datetime
import pytest

from custom_components.gv_smart_home.helpers import (
    get_base_block,
    get_current_block,
    get_prev_next_block_info,
)

# --- Mocking imported calendar functions ---
# We mock because real holiday/weekend logic is irrelevant for helper correctness.
def mock_weekend(date):
    return False

def mock_holiday(date):
    return False

@pytest.fixture(autouse=True)
def patch_calendar(monkeypatch):
    monkeypatch.setattr(
        "custom_components.gv_smart_home.helpers.energy.is_weekend",
        mock_weekend,
    )
    monkeypatch.setattr(
        "custom_components.gv_smart_home.helpers.energy.is_holiday",
        mock_holiday,
    )


# ---------------------------------------------------------------------
# get_base_block tests
# ---------------------------------------------------------------------

@pytest.mark.parametrize("hour,expected", [
    (0, 3),
    (3, 3),
    (5, 3),
    (6, 2),
    (7, 1),
    (10, 1),
    (13, 1),
    (14, 2),
    (15, 2),
    (16, 1),
    (19, 1),
    (20, 2),
    (21, 2),
    (22, 3),
    (23, 3),
])
def test_get_base_block_valid(hour, expected):
    assert get_base_block(hour) == expected


def test_get_base_block_invalid():
    with pytest.raises(ValueError):
        get_base_block(24)


# ---------------------------------------------------------------------
# get_effective_block tests (workday normal conditions)
# ---------------------------------------------------------------------

def test_effective_block_high_season_workday():
    date = datetime.date(2024, 12, 5)  # high season
    assert get_current_block(date, 7) == 1  # base=1 -> no offset


def test_current_block_high_season_free_day(monkeypatch):
    # Free day = weekend or holiday
    monkeypatch.setattr(
        "custom_components.gv_smart_home.helpers.energy.is_weekend",
        lambda d: True,
    )
    date = datetime.date(2024, 12, 5)
    assert get_current_block(date, 7) == 2  # base=1 -> +1


def test_current_block_low_season_workday():
    date = datetime.date(2024, 5, 5)  # low season
    assert get_current_block(date, 7) == 2  # base=1 -> +1


def test_current_block_low_season_free_day(monkeypatch):
    monkeypatch.setattr(
        "custom_components.gv_smart_home.helpers.energy.is_weekend",
        lambda d: True,
    )
    date = datetime.date(2024, 5, 5)
    assert get_current_block(date, 7) == 3  # base=1 -> +2


# ---------------------------------------------------------------------
# prev/next block info tests
# ---------------------------------------------------------------------

def test_prev_next_middle_of_day():
    now = datetime.datetime(2024, 12, 5, 10, 30)  # 10:30
    info = get_prev_next_block_info(now)
    assert info["current_block"] == get_current_block(now.date(), 10)
    assert info["previous_block"] == get_current_block(now.date(), 9)
    assert info["next_block"] == get_current_block(now.date(), 11)
    assert info["minutes_since_previous"] == 30
    assert info["minutes_to_next"] == 30


def test_prev_next_midnight_transition():
    now = datetime.datetime(2024, 5, 5, 0, 10)  # 00:10
    info = get_prev_next_block_info(now)
    assert info["previous_block"] == get_current_block(
        now.date() - datetime.timedelta(days=1), 23
    )
    assert info["current_block"] == get_current_block(now.date(), 0)
    assert info["next_block"] == get_current_block(now.date(), 1)


def test_prev_next_23h_transition():
    now = datetime.datetime(2024, 5, 5, 23, 50)
    info = get_prev_next_block_info(now)
    assert info["next_block"] == get_current_block(
        now.date() + datetime.timedelta(days=1), 0
    )


# ---------------------------------------------------------------------
# edge: season boundary transitions
# ---------------------------------------------------------------------

def test_season_boundary_feb_28():
    date = datetime.date(2024, 2, 28)
    assert get_current_block(date, 7) == 1  # high season workday


def test_season_boundary_mar_1():
    date = datetime.date(2024, 3, 1)
    assert get_current_block(date, 7) == 2  # low season workday (base=1 +1)
