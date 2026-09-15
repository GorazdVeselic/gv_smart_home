"""Varovalka po fazah (spec 6.1, 6.2a, 6.6).

Števec javlja tok na cel amper, zato se tok računa iz moči in napetosti faze.
Predznak števca: pozitivno oddaja, negativno uvoz. Šteje samo uvoz.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_VOLTAGE = 230.0

Triple = tuple[float, float, float]


@dataclass(frozen=True)
class PhaseCurrents:
    """Uvoz po fazah v kW in napetost faze v V. Nedosegljiva napetost je 230 V."""

    import_kw: Triple
    voltage_v: Triple

    @classmethod
    def from_power_w(cls, power_w: tuple[float, float, float], voltage_v: tuple[float | None, float | None, float | None]) -> PhaseCurrents:
        imp = tuple(max(-p, 0.0) / 1000.0 for p in power_w)
        volt = tuple(u if u else DEFAULT_VOLTAGE for u in voltage_v)
        return cls(imp, volt)  # type: ignore[arg-type]


def phase_currents_a(p: PhaseCurrents) -> Triple:
    """Tok uvoza na fazi: max(-P_x, 0) / U_x."""
    return tuple(kw * 1000.0 / u for kw, u in zip(p.import_kw, p.voltage_v))  # type: ignore[return-value]


def house_currents_a(p: PhaseCurrents, i_ev_a: float) -> Triple:
    """I_house_x: tok faze brez avta. Avto vleče na vseh fazah enako."""
    return tuple(i - i_ev_a for i in phase_currents_a(p))  # type: ignore[return-value]


def fuse_limit_a(fuse_a: float, margin_a: float) -> float:
    return fuse_a - margin_a


def headroom_a(house_a: Triple, fuse_a: float, margin_a: float) -> float:
    """I_headroom: prostor do roba na najslabši fazi, navzgor omejen na rob (tudi ob oddaji)."""
    limit = fuse_limit_a(fuse_a, margin_a)
    return min(limit - max(house_a), limit)


def over_fuse_limit(p: PhaseCurrents, fuse_a: float, margin_a: float) -> bool:
    """Trdi prag varovalke: katerakoli faza nad robom."""
    limit = fuse_limit_a(fuse_a, margin_a)
    return any(i > limit for i in phase_currents_a(p))
