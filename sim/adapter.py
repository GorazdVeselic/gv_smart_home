"""Adapter za simulacijo: AdapterCore iz core.sequences izvaja na modelu naprave."""

from __future__ import annotations

import datetime

from core.levels import Level
from core.models import Decision
from core.sequences import CMD_CAR_LIMIT, CMD_CAR_START, CMD_WB_CURRENT, CMD_WB_ENABLE, AdapterCore, Observation, Step

from .plant import Plant


class SimAdapter:
    def __init__(self, plant: Plant, levels: list[Level]) -> None:
        self.plant = plant
        self.core = AdapterCore(levels)

    @property
    def level(self) -> str | None:
        return self.core.level

    @property
    def busy(self) -> bool:
        return self.core.busy

    @property
    def log(self):
        return self.core.log

    @property
    def timeouts(self) -> int:
        return self.core.timeouts

    @property
    def skipped_busy(self) -> int:
        return self.core.skipped_busy

    @property
    def rate_limited(self) -> int:
        return self.core.rate_limited

    def _obs(self) -> Observation:
        return Observation(self.plant.wb_current, self.plant.status, self.plant.p_ev_kw)

    def _execute(self, steps: list[Step], now: datetime.datetime) -> None:
        for s in steps:
            if s.cmd == CMD_WB_CURRENT:
                self.plant.set_wb_current(s.value)
            elif s.cmd == CMD_WB_ENABLE:
                self.plant.set_wb_enabled(s.value)
            elif s.cmd == CMD_CAR_LIMIT:
                self.plant.set_car_limit(now, s.value)
            elif s.cmd == CMD_CAR_START:
                self.plant.start_car(now)

    def hard_threshold(self, now: datetime.datetime) -> None:
        self._execute(self.core.hard_threshold(now), now)

    def apply(self, d: Decision, now: datetime.datetime) -> None:
        self._execute(self.core.apply(d, now, self._obs()), now)

    def advance(self, now: datetime.datetime) -> None:
        self._execute(self.core.advance(now, self._obs()), now)
