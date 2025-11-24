import datetime

def is_weekday(date: datetime.date) -> bool:
    """Return True if given date is a weekday (Monday–Friday)."""
    return date.weekday() < 5  # Monday=0, Sunday=6


def is_weekend(date: datetime.date) -> bool:
    """Return True if given date is a weekend (Saturday or Sunday)."""
    return date.weekday() >= 5  # Saturday=5, Sunday=6


def calculate_easter_date(year: int) -> datetime.date:
    """Return Easter Sunday date for given year (Gregorian calendar).

    Uses Meeus/Jones/Butcher algorithm.
    """
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return datetime.date(year, month, day)


def _get_holidays_for_year(year: int) -> list[tuple[datetime.date, str]]:
    """Return list of (date, name) for Slovenian holidays in a given year."""

    fixed_holidays = {
        (1, 1): "Novo leto",
        (1, 2): "Novo leto (2. dan)",
        (2, 8): "Prešernov dan",
        (4, 27): "Dan upora proti okupatorju",
        (5, 1): "Praznik dela (1. dan)",
        (5, 2): "Praznik dela (2. dan)",
        (6, 25): "Dan državnosti",
        (8, 15): "Marijino vnebovzetje",
        (10, 31): "Dan reformacije",
        (11, 1): "Dan spomina na mrtve",
        (12, 25): "Božič",
        (12, 26): "Dan samostojnosti in enotnosti",
    }

    holidays: list[tuple[datetime.date, str]] = []

    # Fixed date holidays
    for (month, day), name in fixed_holidays.items():
        holidays.append((datetime.date(year, month, day), name))

    # Movable holidays based on Easter
    easter = calculate_easter_date(year)
    holidays.append((easter, "Velika noč"))
    holidays.append((easter + datetime.timedelta(days=1), "Velikonočni ponedeljek"))

    # Pentecost (Whit Sunday) – church holiday, not work-free, but useful for energy logic
    pentecost = easter + datetime.timedelta(days=49)
    holidays.append((pentecost, "Binkošti"))

    # Sort by date for deterministic ordering
    holidays.sort(key=lambda item: item[0])
    return holidays


def is_holiday(date: datetime.date) -> bool:
    """Return True if given date is a Slovenian holiday."""
    holidays = _get_holidays_for_year(date.year)
    return any(h_date == date for h_date, _ in holidays)


def get_holiday_name(date: datetime.date) -> str | None:
    """Return the holiday name for the given date, or None if not a holiday."""
    holidays = _get_holidays_for_year(date.year)
    for h_date, name in holidays:
        if h_date == date:
            return name
    return None


def get_next_holiday(date: datetime.date) -> tuple[datetime.date | None, str | None]:
    """Return the next holiday strictly after the given date.

    Returns (holiday_date, holiday_name) or (None, None) if none is found.
    """
    # We include holidays from this year and next year to handle year-end.
    holidays = _get_holidays_for_year(date.year) + _get_holidays_for_year(date.year + 1)

    future = [(h_date, name) for h_date, name in holidays if h_date > date]
    if not future:
        return None, None

    # Since holidays list is sorted, the first future one is the next holiday.
    next_date, next_name = future[0]
    return next_date, next_name
