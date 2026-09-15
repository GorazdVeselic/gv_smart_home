"""Adapter za simulacijo: izvede Decision po zaporedjih iz spec 6.5 in 6.6.

Eno zaporedje naenkrat. Med oblačnim zaporedjem se odločitve samo beležijo.
Isti oblačni ukaz največ enkrat na 10 min.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field

from core.levels import CAR_LIMIT_MAX, TIER_HIGH, TIER_LOW, TIER_PAUSED, Level, level_by_name
from core.models import Decision

from .plant import CAR_LIMIT_KW, Plant

CONFIRM_BAND_KW = 0.4
LIMIT_TIMEOUT = datetime.timedelta(seconds=40)
START_TIMEOUT = datetime.timedelta(seconds=60)
RESUME_GAP = datetime.timedelta(seconds=20)
SAME_CLOUD_COMMAND_GAP = datetime.timedelta(minutes=10)
IDLE_WB_CURRENT = 6


@dataclass
class Sequence:
    kind: str
    started: datetime.datetime
    deadline: datetime.datetime
    expected_kw: float | None = None
    next_step_at: datetime.datetime | None = None
    target: Level | None = None


@dataclass
class SimAdapter:
    plant: Plant
    levels: list[Level]
    level: str | None = None
    seq: Sequence | None = None
    timeouts: int = 0
    skipped_busy: int = 0
    rate_limited: int = 0
    log: list[tuple[datetime.datetime, str]] = field(default_factory=list)
    _last_cloud: dict[str, datetime.datetime] = field(default_factory=dict)

    @property
    def busy(self) -> bool:
        return self.seq is not None

    # ------------------------------------------------------------------
    def hard_threshold(self, now: datetime.datetime) -> None:
        """Trdi prag: v ravni high wallbox na 6 A takoj (spec 6.4)."""
        if self.level and level_by_name(self.levels, self.level).tier == TIER_HIGH:
            self.plant.set_wb_current(IDLE_WB_CURRENT)
            self.level = f"wb_{IDLE_WB_CURRENT}A"
            self.log.append((now, "hard_threshold wb->6A"))

    def apply(self, d: Decision, now: datetime.datetime) -> None:
        if d.level is None:
            if self.level is not None:
                self.plant.set_wb_current(IDLE_WB_CURRENT)
                self.log.append((now, f"idle ({d.reason})"))
            self.level = None
            self.seq = None
            return
        if d.level == self.level:
            return
        if self.busy:
            self.skipped_busy += 1
            return

        new = level_by_name(self.levels, d.level)
        cur = level_by_name(self.levels, self.level) if self.level else None
        self.log.append((now, f"{self.level} -> {new.name} ({d.reason})"))

        if new.tier == TIER_PAUSED:
            self.plant.set_wb_enabled(False)
            self.level = new.name
            return

        if cur is not None and cur.tier == TIER_PAUSED:
            # vrnitev iz pavze: meja avta, 20 s, enable on + zagon
            if not self._cloud_ok(now, f"limit:{new.car_limit}"):
                return
            self.plant.set_car_limit(now, new.car_limit or CAR_LIMIT_MAX)
            self.seq = Sequence("resume", now, now + RESUME_GAP + START_TIMEOUT, expected_kw=new.power_kw, next_step_at=now + RESUME_GAP, target=new)
            self.level = new.name
            return

        if new.tier == TIER_HIGH:
            self.plant.set_wb_current(new.wb_current)
            if cur is None or cur.tier != TIER_HIGH:
                if not self._cloud_ok(now, f"limit:{CAR_LIMIT_MAX}"):
                    self.level = new.name
                    return
                self.plant.set_car_limit(now, CAR_LIMIT_MAX)
                self.seq = Sequence("raise", now, now + LIMIT_TIMEOUT, expected_kw=new.power_kw)
            self.level = new.name
            return

        # new.tier == TIER_LOW
        self.plant.set_wb_current(new.wb_current)
        if not self._cloud_ok(now, f"limit:{new.car_limit}"):
            return
        self.plant.set_car_limit(now, new.car_limit or "6A")
        self.seq = Sequence("lower" if cur is None or cur.tier == TIER_HIGH else "low_adjust", now, now + LIMIT_TIMEOUT, expected_kw=new.power_kw)
        self.level = new.name

    def advance(self, now: datetime.datetime) -> None:
        """Nadaljuje zaporedje: naslednji korak, potrditev prek P_ev, časovna meja."""
        s = self.seq
        if s is None:
            return
        if s.next_step_at is not None and now >= s.next_step_at:
            s.next_step_at = None
            self.plant.set_wb_enabled(True)
            if not self._cloud_ok(now, "start"):
                self.seq = None
                return
            self.plant.start_car(now)
            return
        if s.next_step_at is not None:
            return
        p_ev = self.plant.p_ev_kw
        if s.expected_kw is not None and abs(p_ev - s.expected_kw) <= CONFIRM_BAND_KW:
            self.seq = None
            return
        if now >= s.deadline:
            self.timeouts += 1
            self.log.append((now, f"timeout {s.kind}"))
            self.seq = None

    def _cloud_ok(self, now: datetime.datetime, key: str) -> bool:
        last = self._last_cloud.get(key)
        if last is not None and now - last < SAME_CLOUD_COMMAND_GAP:
            self.rate_limited += 1
            self.log.append((now, f"rate_limited {key}"))
            return False
        self._last_cloud[key] = now
        return True
