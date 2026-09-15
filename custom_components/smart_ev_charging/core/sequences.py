"""Zaporedja ukazov adapterja (spec 6.5, 6.6), brez HA.

`plan_transition` iz trenutne in ciljne stopnje naredi seznam korakov s
potrditvijo in časovno mejo. `AdapterCore` vodi eno zaporedje naenkrat, ga
potrjuje iz opazovanja wallboxa, oblačni ukaz enkrat ponovi, tapering avta ne
šteje za napako in isti oblačni ukaz pošlje največ enkrat na 10 min. Kdo ukaz
dejansko pošlje (model naprave v simulaciji, service call v HA), je zunaj.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any

from .levels import CAR_LIMIT_MAX, TIER_HIGH, TIER_LOW, TIER_PAUSED, Level, level_by_name
from .models import STATUS_CHARGING, STATUS_PAUSED, Decision

CMD_WB_CURRENT = "wb_current"
CMD_WB_ENABLE = "wb_enable"
CMD_CAR_LIMIT = "car_limit"
CMD_CAR_START = "car_start"
CMD_WAIT = "wait"
CLOUD_CMDS = (CMD_CAR_LIMIT, CMD_CAR_START)

CONFIRM_NONE = "none"
CONFIRM_WB_CURRENT = "wb_current"
CONFIRM_WB_PAUSED = "wb_paused"
CONFIRM_WB_RUNNING = "wb_running"
CONFIRM_P_EV_BAND = "p_ev_band"
CONFIRM_P_EV_STARTED = "p_ev_started"

WB_TIMEOUT_S = 10.0
LIMIT_TIMEOUT_S = 40.0
START_TIMEOUT_S = 60.0
RESUME_GAP_S = 20
CONFIRM_BAND_KW = 0.4
STARTED_KW = 0.5
SAME_CLOUD_COMMAND_GAP = datetime.timedelta(minutes=10)

OUTCOME_SENT = "sent"
OUTCOME_CONFIRMED = "confirmed"
OUTCOME_TIMEOUT = "timeout"
OUTCOME_TAPERING = "tapering"


@dataclass(frozen=True)
class Step:
    cmd: str
    value: Any
    confirm: str = CONFIRM_NONE
    timeout_s: float = 0.0
    expected_kw: float | None = None

    @property
    def is_cloud(self) -> bool:
        return self.cmd in CLOUD_CMDS


@dataclass(frozen=True)
class Observation:
    wb_current: int
    wb_status: str
    p_ev_kw: float


def confirmed(step: Step, obs: Observation) -> bool:
    if step.confirm == CONFIRM_NONE:
        return True
    if step.confirm == CONFIRM_WB_CURRENT:
        return obs.wb_current == step.value
    if step.confirm == CONFIRM_WB_PAUSED:
        return obs.wb_status == STATUS_PAUSED
    if step.confirm == CONFIRM_WB_RUNNING:
        return obs.wb_status != STATUS_PAUSED
    if step.confirm == CONFIRM_P_EV_BAND:
        return step.expected_kw is not None and abs(obs.p_ev_kw - step.expected_kw) <= CONFIRM_BAND_KW
    if step.confirm == CONFIRM_P_EV_STARTED:
        return obs.p_ev_kw > STARTED_KW
    raise ValueError(step.confirm)


def tapering(step: Step, obs: Observation) -> bool:
    """Avto sam vleče manj od stopnje (spec 6.6): ni napaka in ni ponovnega poskusa."""
    return (
        step.confirm == CONFIRM_P_EV_BAND
        and step.expected_kw is not None
        and obs.wb_status == STATUS_CHARGING
        and 0.0 < obs.p_ev_kw < step.expected_kw - CONFIRM_BAND_KW
    )


def wb_floor(levels: list[Level]) -> int:
    return min(lv.wb_current for lv in levels if lv.tier == TIER_HIGH)


def plan_transition(cur: Level | None, new: Level, levels: list[Level]) -> tuple[str, list[Step]]:
    """Vrne vrsto prehoda in korake. Neznana trenutna stopnja šteje kot high (avto na Max)."""
    floor = wb_floor(levels)
    wb = lambda amps: Step(CMD_WB_CURRENT, amps, CONFIRM_WB_CURRENT, WB_TIMEOUT_S)  # noqa: E731
    limit = lambda lv: Step(CMD_CAR_LIMIT, lv.car_limit, CONFIRM_P_EV_BAND, LIMIT_TIMEOUT_S, lv.power_kw)  # noqa: E731
    cur_tier = cur.tier if cur else TIER_HIGH

    if new.tier == TIER_PAUSED:
        return "pause", [Step(CMD_WB_ENABLE, False, CONFIRM_WB_PAUSED, WB_TIMEOUT_S)]
    if cur_tier == TIER_PAUSED:
        return "resume", [
            Step(CMD_CAR_LIMIT, new.car_limit if new.tier == TIER_LOW else CAR_LIMIT_MAX),
            Step(CMD_WAIT, RESUME_GAP_S),
            Step(CMD_WB_ENABLE, True, CONFIRM_WB_RUNNING, WB_TIMEOUT_S),
            Step(CMD_CAR_START, True, CONFIRM_P_EV_STARTED, START_TIMEOUT_S),
        ]
    if new.tier == TIER_HIGH:
        if cur_tier == TIER_HIGH:
            return "high_adjust", [wb(new.wb_current)]
        return "raise", [wb(new.wb_current), limit(new)]
    # new.tier == TIER_LOW
    if cur_tier == TIER_LOW:
        return "low_adjust", [limit(new)]
    return "lower", [wb(floor), limit(new)]


class SequenceRunner:
    def __init__(self, kind: str, steps: list[Step]) -> None:
        self.kind = kind
        self.steps = steps
        self.idx = 0
        self.sending = True
        self.deadline: datetime.datetime | None = None
        self.retried = False
        self.result: str | None = None
        self.failed: Step | None = None

    @property
    def current(self) -> Step:
        return self.steps[self.idx]

    def advance(self, now: datetime.datetime, obs: Observation) -> list[Step]:
        to_send: list[Step] = []
        while self.result is None:
            step = self.current
            if self.sending:
                self.sending = False
                if step.cmd == CMD_WAIT:
                    self.deadline = now + datetime.timedelta(seconds=step.value)
                    return to_send
                to_send.append(step)
                self.deadline = now + datetime.timedelta(seconds=step.timeout_s)
                if step.confirm == CONFIRM_NONE:
                    self._next()
                    continue
                return to_send
            if step.cmd == CMD_WAIT:
                if self.deadline is not None and now >= self.deadline:
                    self._next()
                    continue
                return to_send
            if confirmed(step, obs):
                self._next()
                continue
            if self.deadline is not None and now >= self.deadline:
                if tapering(step, obs):
                    self.result = OUTCOME_TAPERING
                    return to_send
                if step.is_cloud and not self.retried:
                    self.retried = True
                    self.sending = True
                    continue
                self.result = OUTCOME_TIMEOUT
                self.failed = step
                return to_send
            return to_send
        return to_send

    def _next(self) -> None:
        self.idx += 1
        self.sending = True
        if self.idx >= len(self.steps):
            self.result = OUTCOME_CONFIRMED


@dataclass
class AdapterCore:
    levels: list[Level]
    level: str | None = None
    runner: SequenceRunner | None = None
    timeouts: int = 0
    skipped_busy: int = 0
    rate_limited: int = 0
    last_command: tuple[str, Any, str] | None = None
    last_command_time: datetime.datetime | None = None
    log: list[tuple[datetime.datetime, str]] = field(default_factory=list)
    _last_cloud: dict[tuple[str, Any], datetime.datetime] = field(default_factory=dict)

    @property
    def busy(self) -> bool:
        return self.runner is not None

    def hard_threshold(self, now: datetime.datetime) -> list[Step]:
        """Trdi prag: v ravni high wallbox na dno takoj, tudi med zaporedjem (spec 6.6)."""
        if self.level is None or level_by_name(self.levels, self.level).tier != TIER_HIGH:
            return []
        floor = wb_floor(self.levels)
        if self.runner is not None and self.runner.kind in ("raise", "high_adjust"):
            self.runner = None
        if self.level == f"wb_{floor}A":
            return []  # že na dnu, vzorci nad pragom se ponavljajo vsakih 10 s
        self.level = f"wb_{floor}A"
        self.log.append((now, f"hard_threshold wb->{floor}A"))
        return [Step(CMD_WB_CURRENT, floor)]

    def apply(self, d: Decision, now: datetime.datetime, obs: Observation) -> list[Step]:
        if d.level is None:
            steps: list[Step] = []
            if self.level is not None:
                steps = [Step(CMD_WB_CURRENT, wb_floor(self.levels))]
                self.log.append((now, f"idle ({d.reason})"))
            self.level = None
            self.runner = None
            return steps
        if d.level == self.level:
            return []
        if self.busy:
            self.skipped_busy += 1
            return []
        new = level_by_name(self.levels, d.level)
        cur = level_by_name(self.levels, self.level) if self.level else None
        kind, steps = plan_transition(cur, new, self.levels)
        for s in steps:
            if s.is_cloud and self._rate_limited(s, now):
                self.rate_limited += 1
                self.log.append((now, f"rate_limited {s.cmd}={s.value}"))
                return []
        self.log.append((now, f"{self.level} -> {new.name} ({d.reason})"))
        self.level = new.name
        self.runner = SequenceRunner(kind, steps)
        return self._advance(now, obs)

    def advance(self, now: datetime.datetime, obs: Observation) -> list[Step]:
        if self.runner is None:
            return []
        return self._advance(now, obs)

    def _advance(self, now: datetime.datetime, obs: Observation) -> list[Step]:
        assert self.runner is not None
        r = self.runner
        sent = r.advance(now, obs)
        for s in sent:
            if s.is_cloud:
                self._last_cloud[(s.cmd, s.value)] = now
                self._note(s, OUTCOME_SENT, now)
        if r.result is not None:
            last_cloud = next((s for s in reversed(r.steps[: r.idx + 1]) if s.is_cloud), None)
            if r.result == OUTCOME_TIMEOUT:
                self.timeouts += 1
                self.log.append((now, f"timeout {r.kind} {r.failed.cmd if r.failed else ''}"))
                if r.failed is not None and r.failed.is_cloud:
                    self._note(r.failed, OUTCOME_TIMEOUT, now)
            elif last_cloud is not None:
                self._note(last_cloud, r.result, now)
            self.runner = None
        return sent

    def _rate_limited(self, step: Step, now: datetime.datetime) -> bool:
        last = self._last_cloud.get((step.cmd, step.value))
        return last is not None and now - last < SAME_CLOUD_COMMAND_GAP

    def _note(self, step: Step, outcome: str, now: datetime.datetime) -> None:
        self.last_command = (step.cmd, step.value, outcome)
        self.last_command_time = now
