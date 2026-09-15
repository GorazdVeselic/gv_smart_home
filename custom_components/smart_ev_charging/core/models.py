"""Podatkovni razredi za decide() (spec 6.4).

Vse vrednosti so že pretvorjene: moč v kW, tok v A, energija okna v kW·min.
`Inputs` je posnetek enega kontrolnega ticka, `RegulatorState` je zgodovina, ki
jo decide() vrne posodobljeno v `Decision.state`.
"""

from __future__ import annotations

import dataclasses
import datetime
from dataclasses import dataclass

from .levels import TIER_HIGH, TIER_LOW, TIER_PAUSED  # noqa: F401  (skupni imenski prostor ravni)

MODE_OFF = "off"
MODE_OBSERVE = "observe"
MODE_TARIFF = "tariff"

TIER_IDLE = "idle"

# Statusi wallboxa, ki jih decide() razlikuje. Ostali statusi štejejo kot polnjenje.
STATUS_CHARGING = "Charging"
STATUS_PAUSED = "Paused"
STATUS_WAITING_CAR = "Connected waiting car"


@dataclass(frozen=True)
class TariffState:
    block: int
    agreed_kw: float
    reserve_kw: float

    @property
    def target_kw(self) -> float:
        """T: mehki cilj za povprečje okna."""
        return self.agreed_kw - self.reserve_kw


@dataclass(frozen=True)
class WindowState:
    energy_kwmin: float
    remaining_min: float


@dataclass(frozen=True)
class ChargerState:
    cable_connected: bool
    status: str
    p_ev_kw: float
    wb_current: int
    car_limit: str | None


@dataclass(frozen=True)
class Inputs:
    now: datetime.datetime
    mode: str
    tariff: TariffState
    window: WindowState
    charger: ChargerState
    p_other_used_kw: float
    i_headroom_a: float

    def at(self, now: datetime.datetime) -> Inputs:
        return dataclasses.replace(self, now=now)

    def with_other(self, p_other_used_kw: float) -> Inputs:
        return dataclasses.replace(self, p_other_used_kw=p_other_used_kw)


@dataclass(frozen=True)
class RegulatorState:
    """Zgodovina med ticki. `level` None pomeni idle."""

    level: str | None = None
    tier_since: datetime.datetime | None = None
    level_since: datetime.datetime | None = None
    ticks_above_raise: int = 0
    ticks_below_lower: int = 0
    ticks_above_resume: int = 0
    ticks_waiting: int = 0
    hard_threshold: bool = False


@dataclass(frozen=True)
class Decision:
    level: str | None
    tier: str
    reason: str
    p_allow_kw: float
    p_ev_allow_kw: float
    candidate: str
    state: RegulatorState
