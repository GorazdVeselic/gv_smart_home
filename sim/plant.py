"""Model wallboxa in avta z izmerjenimi zamiki (spec 2).

- Wallbox: tok in enable takoj (lokalno). Enable off ustavi polnjenje in konča
  sejo, avto izgubi svojo mejo (nazaj na Max).
- Avto: meja in zagon prek oblaka z zamikom. Ob priklopu kabla začne sam na Max.
- Moč: meja avta 6A = 1,6 kW, 8A = 2,0 kW, 16A = 3,9 kW, Max = tok wallboxa × kw_per_amp.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Callable

from core.levels import CAR_LIMIT_MAX, DEFAULT_KW_PER_AMP
from core.models import STATUS_CHARGING, STATUS_PAUSED, STATUS_WAITING_CAR, ChargerState

CAR_LIMIT_KW = {"6A": 1.6, "8A": 2.0, "16A": 3.9}
CLOUD_LIMIT_DELAY = datetime.timedelta(seconds=18)
CLOUD_START_DELAY = datetime.timedelta(seconds=19)
SELF_START_DELAY = datetime.timedelta(seconds=19)
VOLTAGE = 230.0


@dataclass
class Plant:
    kw_per_amp: float = DEFAULT_KW_PER_AMP
    wb_current: int = 6
    wb_enabled: bool = True
    cable: bool = False
    car_limit: str = CAR_LIMIT_MAX
    car_charging: bool = False
    need_kwh: float | None = None
    charged_kwh: float = 0.0
    cloud_commands: int = 0
    _pending: list[tuple[datetime.datetime, Callable[[], None]]] = field(default_factory=list)

    # lokalni ukazi
    def set_wb_current(self, amps: int) -> None:
        self.wb_current = max(6, min(32, amps))

    def set_wb_enabled(self, on: bool) -> None:
        if self.wb_enabled and not on:
            self.car_charging = False
            self.car_limit = CAR_LIMIT_MAX  # seja se konča, meja se izgubi
        self.wb_enabled = on

    # oblačni ukazi
    def set_car_limit(self, now: datetime.datetime, limit: str) -> None:
        self.cloud_commands += 1

        def apply() -> None:
            self.car_limit = limit

        self._pending.append((now + CLOUD_LIMIT_DELAY, apply))

    def start_car(self, now: datetime.datetime) -> None:
        self.cloud_commands += 1

        def apply() -> None:
            if self.cable and self.wb_enabled and not self.full:
                self.car_charging = True

        self._pending.append((now + CLOUD_START_DELAY, apply))

    # kabel
    def plug_in(self, now: datetime.datetime) -> None:
        self.cable = True
        self.car_limit = CAR_LIMIT_MAX

        def apply() -> None:
            if self.cable and self.wb_enabled and not self.full:
                self.car_charging = True

        self._pending.append((now + SELF_START_DELAY, apply))

    def plug_out(self) -> None:
        self.cable = False
        self.car_charging = False

    # čas
    def advance(self, now: datetime.datetime, dt: datetime.timedelta) -> None:
        due = [p for p in self._pending if p[0] <= now]
        self._pending = [p for p in self._pending if p[0] > now]
        for _, fn in due:
            fn()
        self.charged_kwh += self.p_ev_kw * dt.total_seconds() / 3600.0
        if self.full and self.car_charging:
            self.car_charging = False

    @property
    def full(self) -> bool:
        return self.need_kwh is not None and self.charged_kwh >= self.need_kwh

    @property
    def p_ev_kw(self) -> float:
        if not (self.cable and self.wb_enabled and self.car_charging):
            return 0.0
        wb_kw = self.wb_current * self.kw_per_amp
        return min(CAR_LIMIT_KW.get(self.car_limit, wb_kw), wb_kw)

    @property
    def i_ev_a(self) -> float:
        return self.p_ev_kw * 1000.0 / (3 * VOLTAGE)

    @property
    def status(self) -> str:
        if not self.wb_enabled:
            return STATUS_PAUSED
        if self.car_charging:
            return STATUS_CHARGING
        return STATUS_WAITING_CAR

    def charger_state(self) -> ChargerState:
        return ChargerState(self.cable, self.status, self.p_ev_kw, self.wb_current, self.car_limit)
