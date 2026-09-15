"""Profili hiše in PV za simulacijo (spec 8).

Hiša po fazah: osnova 0,5 kW enakomerno, toplotna črpalka 2,5 kW trifazno v
ciklih (15 min vsako uro), pečica 3 kW na fazi B od 18h do 19h s termostatom.
Profil se po 24-urnem posnetku zamenja z izmerjenim.
"""

from __future__ import annotations

import datetime
import math

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
