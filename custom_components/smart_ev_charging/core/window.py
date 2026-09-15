"""Proračun 15-minutnega obračunskega okna (spec 6.2).

Okna so poravnana na uro (00, 15, 30, 45). Šteje samo prevzem (uvoz), zato
klicatelj poda `p_import_kw >= 0`. Energija se integrira časovno uteženo:
prejšnja vrednost velja do naslednjega vzorca.

Enote: moč v kW, energija v kW·min, čas v minutah.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass

WINDOW_MINUTES = 15
MIN_REMAINING_FOR_BUDGET = 1.0


def allowed_import_kw(energy_kwmin: float, remaining_min: float, target_kw: float, agreed_kw: float) -> float:
    """P_allow: dovoljen povprečni uvoz do konca okna, da povprečje okna ostane pod ciljem.

    Omejen navzgor z dogovorjeno močjo. V zadnji minuti okna velja kar cilj.
    """
    if remaining_min < MIN_REMAINING_FOR_BUDGET:
        return min(target_kw, agreed_kw)
    allow_avg = (target_kw * WINDOW_MINUTES - energy_kwmin) / remaining_min
    return min(allow_avg, agreed_kw)


def projected_average_kw(energy_kwmin: float, remaining_min: float, p_import_rest_kw: float) -> float:
    """Povprečje okna, če do konca okna uvoz ostane p_import_rest_kw."""
    return (energy_kwmin + max(p_import_rest_kw, 0.0) * remaining_min) / WINDOW_MINUTES


def window_start(now: datetime.datetime) -> datetime.datetime:
    return now.replace(minute=(now.minute // WINDOW_MINUTES) * WINDOW_MINUTES, second=0, microsecond=0)


def _minutes(delta: datetime.timedelta) -> float:
    return delta.total_seconds() / 60.0


@dataclass(frozen=True)
class ClosedWindow:
    start: datetime.datetime
    average_kw: float
    agreed_kw: float | None

    @property
    def exceeded(self) -> bool:
        return self.agreed_kw is not None and self.average_kw > self.agreed_kw


class WindowBudget:
    def __init__(self, now: datetime.datetime) -> None:
        self._start = window_start(now)
        self._energy = 0.0
        self._last_ts: datetime.datetime | None = None
        self._last_p = 0.0
        self.last_window: ClosedWindow | None = None
        self._agreed_for_close: float | None = None

    # ------------------------------------------------------------------
    # stanje
    # ------------------------------------------------------------------
    @property
    def start(self) -> datetime.datetime:
        return self._start

    @property
    def energy_kwmin(self) -> float:
        return self._energy

    def elapsed(self, now: datetime.datetime) -> float:
        return min(max(_minutes(now - self._start), 0.0), WINDOW_MINUTES)

    def remaining(self, now: datetime.datetime) -> float:
        return WINDOW_MINUTES - self.elapsed(now)

    def average_so_far(self, now: datetime.datetime) -> float:
        el = self.elapsed(now)
        return self._energy / el if el > 0 else 0.0

    # ------------------------------------------------------------------
    # vzorci
    # ------------------------------------------------------------------
    def add_sample(self, now: datetime.datetime, p_import_kw: float, agreed_kw: float | None = None) -> None:
        """Doda vzorec. Ob prehodu čez mejo okna zapre staro okno in odpre novo."""
        p_import_kw = max(p_import_kw, 0.0)
        self._agreed_for_close = agreed_kw
        if self._last_ts is None or now < self._last_ts:
            self._reset_to(now)
            self._last_ts, self._last_p = now, p_import_kw
            return

        end = self._start + datetime.timedelta(minutes=WINDOW_MINUTES)
        if now >= end:
            # prejšnja vrednost velja do konca starega okna
            self._energy += self._last_p * _minutes(end - self._last_ts)
            self._close(agreed_kw)
            self._reset_to(now)
            # in od začetka novega okna do tega vzorca (vmes preskočena okna se izgubijo)
            self._energy = self._last_p * _minutes(now - self._start)
        else:
            self._energy += self._last_p * _minutes(now - self._last_ts)

        self._last_ts, self._last_p = now, p_import_kw

    def restore_estimate(self, now: datetime.datetime, p_import_kw: float) -> None:
        """Po zagonu sredi okna: predpostavi trenutni uvoz za ves pretečeni čas."""
        self._reset_to(now)
        self._energy = max(p_import_kw, 0.0) * self.elapsed(now)
        self._last_ts, self._last_p = now, max(p_import_kw, 0.0)

    def _reset_to(self, now: datetime.datetime) -> None:
        self._start = window_start(now)
        self._energy = 0.0

    def _close(self, agreed_kw: float | None) -> None:
        self.last_window = ClosedWindow(self._start, self._energy / WINDOW_MINUTES, agreed_kw)

    # ------------------------------------------------------------------
    # proračun
    # ------------------------------------------------------------------
    def allowed_import_kw(self, now: datetime.datetime, target_kw: float, agreed_kw: float) -> float:
        return allowed_import_kw(self._energy, self.remaining(now), target_kw, agreed_kw)

    def projected_average_kw(self, now: datetime.datetime, p_import_rest_kw: float) -> float:
        return projected_average_kw(self._energy, self.remaining(now), p_import_rest_kw)
