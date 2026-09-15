"""Zanka simulacije dneva: števec vsakih 10 s, tick vsakih 30 s, korak 1 s.

Zagon: .venv/bin/python -m sim.run --date 2026-12-08 --pv winter --reserve 2
"""

from __future__ import annotations

import argparse
import datetime
from dataclasses import dataclass, field

import sim  # noqa: F401  (pot do core)
from core.controller import Config, Controller
from core.fuse import PhaseCurrents, fuse_limit_a
from core.models import MODE_TARIFF
from core.window import ClosedWindow

from .adapter import SimAdapter
from .plant import VOLTAGE, Plant
from .profiles import MeasuredProfile, house_kw, pv_kw

METER_PERIOD = 10
TICK_PERIOD = 30
STEP = datetime.timedelta(seconds=1)


@dataclass
class Result:
    windows: list[ClosedWindow] = field(default_factory=list)
    max_phase_a: float = 0.0
    longest_over_fuse_s: int = 0
    longest_over_fuse_avoidable_s: int = 0
    hard_thresholds: int = 0
    cloud_commands: int = 0
    charged_kwh: float = 0.0
    imported_kwh: float = 0.0
    timeouts: int = 0
    rate_limited: int = 0
    skipped_busy: int = 0
    level_changes: int = 0
    reasons: dict[str, int] = field(default_factory=dict)
    log: list[tuple[datetime.datetime, str]] = field(default_factory=list)

    @property
    def windows_over(self) -> list[ClosedWindow]:
        return [w for w in self.windows if w.exceeded]

    def summary(self) -> str:
        lines = [
            f"oken čez dogovorjeno: {len(self.windows_over)} od {len(self.windows)}",
            f"najvišji tok faze: {self.max_phase_a:.1f} A, najdaljše preseganje roba: {self.longest_over_fuse_s} s"
            f" (ki bi ga dno car_6A odpravilo: {self.longest_over_fuse_avoidable_s} s), trdih pragov: {self.hard_thresholds}",
            f"oblačnih ukazov: {self.cloud_commands}, časovnih mej: {self.timeouts}, omejenih: {self.rate_limited}, preskočenih (zasedeno): {self.skipped_busy}",
            f"menjav stopnje: {self.level_changes}",
            f"napolnjeno: {self.charged_kwh:.1f} kWh, uvoz: {self.imported_kwh:.1f} kWh",
        ]
        return "\n".join(lines)


def simulate(
    date: datetime.date,
    pv: str,
    cfg: Config,
    plug_in: datetime.time = datetime.time(0, 0),
    plug_out: datetime.time | None = None,
    need_kwh: float | None = None,
    mode: str = MODE_TARIFF,
    profile: MeasuredProfile | None = None,
) -> Result:
    """pv: 'none', 'clear', 'cloudy', 'winter' za sintetični profil; z `profile` se hiša in PV bereta iz posnetka."""
    start = datetime.datetime.combine(date, datetime.time(0, 0))
    ctl = Controller(cfg, start)
    plant = Plant(kw_per_amp=cfg.kw_per_amp, need_kwh=need_kwh)
    adapter = SimAdapter(plant, ctl.levels)
    res = Result()
    limit_a = fuse_limit_a(cfg.fuse_a, cfg.fuse_margin_a)
    over_s = 0
    over_avoidable_s = 0
    floor_kw = min(lv.power_kw for lv in ctl.levels if lv.power_kw > 0)
    floor_a = floor_kw * 1000 / (3 * VOLTAGE)
    last_window_start = ctl.window.start

    now = start
    for t in range(24 * 3600):
        if now.time() == plug_in and not plant.cable and t < 24 * 3600 - 1:
            plant.plug_in(now)
        if plug_out is not None and now.time() == plug_out and plant.cable:
            plant.plug_out()
        plant.advance(now, STEP)
        adapter.advance(now)

        if profile is not None:
            house = profile.house_kw(now)
            pv_total = profile.pv_kw(now)
        else:
            house = house_kw(now)
            pv_total = pv_kw(now, pv)
        p_ev = plant.p_ev_kw
        phase_grid = tuple(pv_total / 3 - h - p_ev / 3 for h in house)  # kW, pozitivno oddaja
        p_grid = sum(phase_grid)
        phases = PhaseCurrents.from_power_w(tuple(p * 1000 for p in phase_grid), (VOLTAGE,) * 3)  # type: ignore[arg-type]
        imports_a = [max(-p, 0.0) * 1000 / VOLTAGE for p in phase_grid]
        res.max_phase_a = max(res.max_phase_a, *imports_a)
        worst_a = max(imports_a)
        if worst_a > limit_a:
            over_s += 1
            res.longest_over_fuse_s = max(res.longest_over_fuse_s, over_s)
            # preseganje, ki bi ga avto na dnu (car_6A) odpravil
            over_avoidable_s = over_avoidable_s + 1 if worst_a - plant.i_ev_a + floor_a <= limit_a else 0
            res.longest_over_fuse_avoidable_s = max(res.longest_over_fuse_avoidable_s, over_avoidable_s)
        else:
            over_s = 0
            over_avoidable_s = 0
        res.imported_kwh += max(-p_grid, 0.0) / 3600

        if t % METER_PERIOD == 0:
            if ctl.on_meter(now, p_grid, phases, p_ev, plant.i_ev_a):
                adapter.hard_threshold(now)
            if ctl.window.start != last_window_start and ctl.window.last_window is not None:
                res.windows.append(ctl.window.last_window)
                last_window_start = ctl.window.start
        if t % TICK_PERIOD == 0:
            d = ctl.tick(now, plant.charger_state(), mode)
            res.reasons[d.reason] = res.reasons.get(d.reason, 0) + 1
            adapter.apply(d, now)
        now += STEP

    res.cloud_commands = plant.cloud_commands
    res.charged_kwh = plant.charged_kwh
    res.timeouts = adapter.timeouts
    res.rate_limited = adapter.rate_limited
    res.skipped_busy = adapter.skipped_busy
    res.log = adapter.log
    res.level_changes = sum(1 for _, msg in adapter.log if "->" in msg)
    res.hard_thresholds = sum(1 for _, msg in adapter.log if msg.startswith("hard_threshold"))
    return res


DEFAULT_BLOCKS = {1: 5.4, 2: 7.1, 3: 10.0, 4: 10.0, 5: 10.0}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", type=datetime.date.fromisoformat, default=datetime.date(2026, 9, 15))
    ap.add_argument("--pv", choices=["none", "clear", "cloudy", "winter"], default="clear")
    ap.add_argument("--reserve", type=float, default=2.0)
    ap.add_argument("--plug-in", type=datetime.time.fromisoformat, default=datetime.time(0, 0))
    ap.add_argument("--need-kwh", type=float, default=None)
    ap.add_argument("--profile", help="CSV iz sim.fetch_profile; nadomesti sintetični profil in --pv")
    ap.add_argument("--log", action="store_true")
    a = ap.parse_args()
    cfg = Config(block_power_kw=DEFAULT_BLOCKS, reserve_kw=a.reserve)
    profile = MeasuredProfile(a.profile) if a.profile else None
    res = simulate(a.date, a.pv, cfg, plug_in=a.plug_in, need_kwh=a.need_kwh, profile=profile)
    print(res.summary())
    print("razlogi:", dict(sorted(res.reasons.items(), key=lambda kv: -kv[1])))
    if a.log:
        for ts, msg in res.log:
            print(ts.strftime("%H:%M:%S"), msg)
    for w in res.windows_over:
        print("čez:", w.start.strftime("%H:%M"), f"{w.average_kw:.2f} > {w.agreed_kw}")


if __name__ == "__main__":
    main()
