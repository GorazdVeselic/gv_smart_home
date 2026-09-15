"""Profili hiše in PV za simulacijo (spec 8).

Hiša po fazah: osnova 0,5 kW enakomerno, toplotna črpalka 2,5 kW trifazno v
ciklih (15 min vsako uro), pečica 3 kW na fazi B od 18h do 19h s termostatom.
Profil se po 24-urnem posnetku zamenja z izmerjenim.
"""

from __future__ import annotations

import csv
import datetime
import math
from pathlib import Path

Triple = tuple[float, float, float]

BASE_KW = 0.5
PUMP_KW = 2.5
OVEN_KW = 3.0


def house_kw(now: datetime.datetime) -> Triple:
    base = BASE_KW / 3
    pump = PUMP_KW / 3 if 20 <= now.minute < 35 else 0.0
    oven = 0.0
    if now.hour == 18:
        # prvih 10 min polna moč, nato termostat 5 min vklop, 5 min izklop
        oven = OVEN_KW if now.minute < 10 or (now.minute // 5) % 2 == 0 else 0.0
    return (base + pump, base + pump + oven, base + pump)


def _bell(now: datetime.datetime, sunrise: float, sunset: float, peak_kw: float) -> float:
    h = now.hour + now.minute / 60 + now.second / 3600
    if h <= sunrise or h >= sunset:
        return 0.0
    return peak_kw * math.sin(math.pi * (h - sunrise) / (sunset - sunrise)) ** 1.5


def pv_kw(now: datetime.datetime, kind: str) -> float:
    if kind == "none":
        return 0.0
    if kind == "clear":
        return _bell(now, 6.0, 20.0, 6.0)
    if kind == "cloudy":
        # oblaki: vsakih 7 min menjava med 25 % in 60 % jasnega
        factor = 0.25 if (now.hour * 60 + now.minute) // 7 % 2 == 0 else 0.6
        return _bell(now, 6.0, 20.0, 6.0) * factor
    if kind == "winter":
        return _bell(now, 8.0, 16.0, 1.5)
    raise ValueError(kind)


class MeasuredProfile:
    """Izmerjeni profil iz sim/fetch_profile.py: hiša po fazah in PV po času dneva.

    Vrstice so na 10 s. Čas se preslika po uri dneva, zato profil velja za
    katerikoli datum (blok se vzame iz datuma simulacije).
    """

    def __init__(self, path: str | Path) -> None:
        self._house: dict[int, Triple] = {}
        self._pv: dict[int, float] = {}
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                t = datetime.datetime.fromisoformat(row["time"])
                key = self._key(t)
                self._house[key] = (
                    max(float(row["house_a_kw"]), 0.0),
                    max(float(row["house_b_kw"]), 0.0),
                    max(float(row["house_c_kw"]), 0.0),
                )
                self._pv[key] = float(row["pv_kw"])
        if not self._house:
            raise ValueError(f"prazen profil: {path}")

    @staticmethod
    def _key(t: datetime.datetime) -> int:
        return (t.hour * 3600 + t.minute * 60 + t.second) // 10

    def house_kw(self, now: datetime.datetime) -> Triple:
        return self._house.get(self._key(now), self._nearest(self._house, now))

    def pv_kw(self, now: datetime.datetime) -> float:
        return self._pv.get(self._key(now), self._nearest(self._pv, now))

    def _nearest(self, table: dict, now: datetime.datetime):
        k = self._key(now)
        best = min(table, key=lambda kk: abs(kk - k))
        return table[best]
