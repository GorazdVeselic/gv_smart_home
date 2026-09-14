from __future__ import annotations

import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class TariffState:
    now: datetime.datetime

    current_block: int
    previous_block: int
    next_block: int

    same_as_previous: bool
    same_as_next: bool

    minutes_since_previous: int
    minutes_to_next: int

    is_high_season: bool
    is_holiday: bool
    is_weekend: bool

    holiday_name: str | None

    next_holiday_date: datetime.date | None
    next_holiday_name: str | None


