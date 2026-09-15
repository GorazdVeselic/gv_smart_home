"""Orkestrator brez HA (spec 5): drži okno, glajenje in zgodovino, kliče decide().

Dva vhoda: on_meter() ob vsakem vzorcu števca (trdi prag) in tick() vsakih
30 s (odločitev). Kaj se z odločitvijo zgodi, je stvar adapterja: v HA
charger.py, v simulaciji model naprave.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field

from .decide import decide, note_hard_threshold
from .fuse import PhaseCurrents, fuse_limit_a, headroom_a, house_currents_a, over_fuse_limit
from .levels import DEFAULT_KW_PER_AMP, Level, build_levels
from .models import ChargerState, Decision, Inputs, RegulatorState, TariffState, WindowState
from .smoothing import RiseFastFallSlow
from .tariff import get_current_block
from .window import WindowBudget

SMOOTHING_WINDOW = datetime.timedelta(minutes=2)


@dataclass(frozen=True)
class Config:
    block_power_kw: dict[int, float]
    reserve_kw: float = 2.0
    fuse_a: float = 20.0
    fuse_margin_a: float = 3.0
    kw_per_amp: float = DEFAULT_KW_PER_AMP
    smoothing: datetime.timedelta = field(default=SMOOTHING_WINDOW)


class Controller:
    def __init__(self, cfg: Config, now: datetime.datetime, levels: list[Level] | None = None) -> None:
        self.cfg = cfg
        self.levels = levels or build_levels(kw_per_amp=cfg.kw_per_amp)
        self.window = WindowBudget(now)
        self.state = RegulatorState()
        self._other = RiseFastFallSlow(cfg.smoothing)
        self._house = [RiseFastFallSlow(cfg.smoothing) for _ in range(3)]
        self.p_other_used_kw = 0.0
        self.i_house_used_a: tuple[float, float, float] = (0.0, 0.0, 0.0)
        self.i_headroom_a = fuse_limit_a(cfg.fuse_a, cfg.fuse_margin_a)
        self.last_decision: Decision | None = None

    def tariff_at(self, now: datetime.datetime) -> TariffState:
        block = get_current_block(now.date(), now.hour)
        return TariffState(block=block, agreed_kw=self.cfg.block_power_kw[block], reserve_kw=self.cfg.reserve_kw)

    def on_meter(
        self,
        now: datetime.datetime,
        p_grid_kw: float,
        phases: PhaseCurrents,
        p_ev_kw: float,
        i_ev_a: float,
    ) -> bool:
        """Vzorec števca. Vrne True, kadar je trdi prag sprožen (klicatelj da wallbox na 6 A)."""
        tariff = self.tariff_at(now)
        p_import = max(-p_grid_kw, 0.0)
        self.window.add_sample(now, p_import, tariff.agreed_kw)
        self.p_other_used_kw = self._other.update(now, -p_grid_kw - p_ev_kw)
        house = house_currents_a(phases, i_ev_a)
        self.i_house_used_a = tuple(sm.update(now, i) for sm, i in zip(self._house, house))  # type: ignore[assignment]
        self.i_headroom_a = headroom_a(self.i_house_used_a, self.cfg.fuse_a, self.cfg.fuse_margin_a)

        if p_import > tariff.agreed_kw or over_fuse_limit(phases, self.cfg.fuse_a, self.cfg.fuse_margin_a):
            self.state = note_hard_threshold(self.state, self.levels)
            return True
        return False

    def tick(self, now: datetime.datetime, charger: ChargerState, mode: str, charge_anyway: bool = False) -> Decision:
        inp = Inputs(
            now=now,
            mode=mode,
            tariff=self.tariff_at(now),
            window=WindowState(self.window.energy_kwmin, self.window.remaining(now)),
            charger=charger,
            p_other_used_kw=self.p_other_used_kw,
            i_headroom_a=self.i_headroom_a,
            charge_anyway=charge_anyway,
        )
        d = decide(inp, self.state, self.levels)
        self.state = d.state
        self.last_decision = d
        return d
