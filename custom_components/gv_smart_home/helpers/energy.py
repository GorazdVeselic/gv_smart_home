import datetime


from .calendar import (
    is_weekend,
    is_holiday,
)


def is_high_season(date: datetime.date) -> bool:
    """
    Return True if the date falls within the high season.

    High season (based on Slovenian electricity tariff rules):
      - November 1st to February 28th/29th (months: 11, 12, 1, 2)

    Low season:
      - March 1st to October 31st

    Adjust if tariff rules change.
    """
    month = date.month
    return month in (11, 12, 1, 2)


def get_base_block(hour: int) -> int:
    """
    Return the base hourly block for a given hour of the day.

    Block mapping:
      00–05 -> 3
      06    -> 2
      07–13 -> 1
      14–15 -> 2
      16–19 -> 1
      20–21 -> 2
      22–23 -> 3
    """
    BLOCKS = [
        ((0, 5), 3),
        ((6, 6), 2),
        ((7, 13), 1),
        ((14, 15), 2),
        ((16, 19), 1),
        ((20, 21), 2),
        ((22, 23), 3),
    ]

    for (start, end), block in BLOCKS:
        if start <= hour <= end:
            return block

    raise ValueError(f"Invalid hour: {hour}")


def get_current_block(date: datetime.date, hour: int) -> int:
    """
    Compute the current block based on:
      - base block (hour-based)
      - season (high/low)
      - whether the day is work-free (weekend/holiday)

    Rules:
      High season:
        workday       -> base
        work-free day -> base + 1

      Low season:
        workday       -> base + 1
        work-free day -> base + 2
    """
    base = get_base_block(hour)
    is_work_free = is_weekend(date) or is_holiday(date)
    high = is_high_season(date)

    # Mapping: (is_high_season, is_free_day) -> offset
    RULES = {
        (True, False): 0,   # high season, workday
        (True, True): 1,    # high season, free day
        (False, False): 1,  # low season, workday
        (False, True): 2,   # low season, free day
    }

    offset = RULES[(high, is_work_free)]
    return base + offset


def get_prev_next_block_info(now: datetime.datetime):
    """
    Return a dictionary describing:
      - previous block
      - current block
      - next block
      - whether blocks match previous/next
      - minutes since previous hour
      - minutes to next hour
    """
    today = now.date()
    current_hour = now.hour

    # Determine previous hour + date
    if current_hour == 0:
        prev_date = today - datetime.timedelta(days=1)
        prev_hour = 23
    else:
        prev_date = today
        prev_hour = current_hour - 1

    # Determine next hour + date
    if current_hour == 23:
        next_date = today + datetime.timedelta(days=1)
        next_hour = 0
    else:
        next_date = today
        next_hour = current_hour + 1

    current_block = get_current_block(today, current_hour)
    previous_block = get_current_block(prev_date, prev_hour)
    next_block = get_current_block(next_date, next_hour)

    # Minutes since previous block (same as current minute)
    minutes_since_prev = now.minute

    # Minutes until next block change
    minutes_to_next = 60 - now.minute

    return {
        "current_block": current_block,
        "previous_block": previous_block,
        "next_block": next_block,
        "same_as_previous": current_block == previous_block,
        "same_as_next": current_block == next_block,
        "minutes_since_previous": minutes_since_prev,
        "minutes_to_next": minutes_to_next,
    }

def get_blocks_for_today(date: datetime.date) -> list[int]:
    """Return a list of 24 tariff blocks for the given date."""
    blocks: list[int] = []

    for hour in range(24):
        blocks.append(get_current_block(date, hour))

    return blocks