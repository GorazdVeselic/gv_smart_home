import datetime

import pytest

from core.tariff import (
    get_base_block,
    get_blocks_for_today,
    get_current_block,
    get_prev_next_block_info,
    is_high_season,
)


@pytest.mark.parametrize(
    "hour,expected",
    [(0, 3), (5, 3), (6, 2), (7, 1), (13, 1), (14, 2), (15, 2), (16, 1), (19, 1), (20, 2), (21, 2), (22, 3), (23, 3)],
)
def test_get_base_block(hour, expected):
    assert get_base_block(hour) == expected


def test_get_base_block_invalid():
    with pytest.raises(ValueError):
        get_base_block(24)


def test_is_high_season():
    assert is_high_season(datetime.date(2024, 11, 1))
    assert is_high_season(datetime.date(2024, 2, 29))
    assert not is_high_season(datetime.date(2024, 3, 1))
    assert not is_high_season(datetime.date(2024, 10, 31))


# 2024-12-05 je četrtek v visoki sezoni, 2024-05-07 je torek v nizki sezoni.
def test_block_high_season_workday():
    assert get_current_block(datetime.date(2024, 12, 5), 7) == 1
    assert get_current_block(datetime.date(2024, 12, 5), 17) == 1
    assert get_current_block(datetime.date(2024, 12, 5), 6) == 2
    assert get_current_block(datetime.date(2024, 12, 5), 23) == 3


def test_block_high_season_free_day():
    saturday = datetime.date(2024, 12, 7)
    assert get_current_block(saturday, 7) == 2
    assert get_current_block(saturday, 23) == 4


def test_block_low_season_workday():
    assert get_current_block(datetime.date(2024, 5, 7), 7) == 2
    assert get_current_block(datetime.date(2024, 5, 7), 23) == 4


def test_block_low_season_free_day_and_holiday():
    assert get_current_block(datetime.date(2024, 5, 4), 7) == 3  # sobota
    assert get_current_block(datetime.date(2024, 5, 1), 7) == 3  # praznik dela, sreda
    assert get_current_block(datetime.date(2024, 5, 4), 23) == 5


def test_prev_next_middle_of_day():
    now = datetime.datetime(2024, 12, 5, 10, 30)
    info = get_prev_next_block_info(now)
    assert info["current_block"] == 1
    assert info["previous_block"] == 1
    assert info["next_block"] == 1
    assert info["minutes_since_previous"] == 30
    assert info["minutes_to_next"] == 30


def test_prev_next_block_change_at_14():
    now = datetime.datetime(2024, 12, 5, 13, 50)
    info = get_prev_next_block_info(now)
    assert info["current_block"] == 1
    assert info["next_block"] == 2
    assert info["same_as_next"] is False
    assert info["minutes_to_next"] == 10


def test_prev_next_midnight_transition():
    now = datetime.datetime(2024, 5, 5, 0, 10)  # nedelja
    info = get_prev_next_block_info(now)
    assert info["previous_block"] == get_current_block(datetime.date(2024, 5, 4), 23)
    assert info["current_block"] == get_current_block(datetime.date(2024, 5, 5), 0)


def test_prev_next_23h_transition_into_workday():
    now = datetime.datetime(2024, 5, 5, 23, 50)  # nedelja -> ponedeljek
    info = get_prev_next_block_info(now)
    assert info["current_block"] == 5
    assert info["next_block"] == 4


def test_season_boundaries():
    assert get_current_block(datetime.date(2024, 2, 28), 7) == 1
    assert get_current_block(datetime.date(2024, 3, 1), 7) == 2


def test_blocks_for_today_length_and_shape():
    blocks = get_blocks_for_today(datetime.date(2024, 12, 5))
    assert len(blocks) == 24
    assert blocks[7] == 1 and blocks[0] == 3
