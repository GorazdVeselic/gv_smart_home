"""decide(): en kontrolni tick regulatorja (spec 6.4).

Čista funkcija: iz posnetka vhodov in zgodovine vrne odločitev in novo
zgodovino. Ne ukazuje in ne pozna HA. Trdi prag teče zunaj (ob vsakem vzorcu
števca) in se sem sporoči z note_hard_threshold().
"""

from __future__ import annotations

import dataclasses
import datetime

from .levels import (
    TIER_HIGH,
    TIER_LOW,
    TIER_PAUSED,
    Level,
    highest_in_tier,
    highest_level_at_or_below,
    level_by_name,
    lowest_charging_level,
    tier_threshold_kw,
)
from .models import (
    MODE_OFF,
    STATUS_PAUSED,
    STATUS_WAITING_CAR,
    TIER_IDLE,
    Decision,
    Inputs,
    RegulatorState,
)
from .window import allowed_import_kw, projected_average_kw

# histereza ravni (korak 4 in 5)
RAISE_MARGIN_KW = 0.5
LOWER_MARGIN_KW = 0.3
RAISE_TICKS = 20
LOWER_TICKS = 2
MIN_LOW_AGE_FOR_RAISE = datetime.timedelta(minutes=10)

# pavza (korak 6)
RESUME_MARGIN_KW = 0.5
RESUME_TICKS = 10
MIN_PAUSE = datetime.timedelta(minutes=10)

# korak 7 in 8
HIGH_STEP_UP_A = 2
HIGH_DEADBAND_A = 1.0
LOW_HOLD = datetime.timedelta(minutes=10)

# avto dosegel cilj SOC (spec 6.6): status čakanja ali P_ev pod pragom več kot 5 min
WAITING_TICKS = 10
NO_POWER_KW = 0.1

# vstop iz idle: P_ev v tem pasu okrog moči stopnje šteje kot potrditev (spec 6.5)
CONFIRM_BAND_KW = 0.4
# pod to močjo avto še ni začel; ob priklopu začne na Max (spec 6.5)
STARTING_P_EV_KW = 0.5

LEVEL_OFF = "off"


def note_hard_threshold(state: RegulatorState, levels: list[Level]) -> RegulatorState:
    """Trdi prag je sprožen: v ravni high je wallbox že na 6 A, zastavica za korak 5."""
    level = state.level
    if level is not None and level_by_name(levels, level).tier == TIER_HIGH:
        level = _wb_level_name(levels, min(lv.wb_current for lv in levels if lv.tier == TIER_HIGH))
    return dataclasses.replace(state, level=level, hard_threshold=True)


def decide(inp: Inputs, state: RegulatorState, levels: list[Level]) -> Decision:
    tariff, win, ch = inp.tariff, inp.window, inp.charger
    p_tier = tier_threshold_kw(levels)
    floor = lowest_charging_level(levels)
    kw_per_amp = _kw_per_amp(levels)

    # korak 2 in 3
    p_allow = allowed_import_kw(win.energy_kwmin, win.remaining_min, tariff.target_kw, tariff.agreed_kw)
    p_ev_allow = min(p_allow - inp.p_other_used_kw, inp.i_headroom_a * kw_per_amp)
    cand = highest_level_at_or_below(levels, p_ev_allow) or floor
    p_proj_floor = projected_average_kw(win.energy_kwmin, win.remaining_min, inp.p_other_used_kw + floor.power_kw)

    def out(level: Level | None, tier: str, reason: str, new_state: RegulatorState) -> Decision:
        return Decision(
            level=level.name if level else None,
            tier=tier,
            reason=reason,
            p_allow_kw=p_allow,
            p_ev_allow_kw=p_ev_allow,
            candidate=cand.name,
            state=dataclasses.replace(new_state, hard_threshold=False),
        )

    # korak 1
    idle = _idle_reason(inp, state)
    if idle:
        return out(None, TIER_IDLE, idle, RegulatorState())

    if state.level is None:
        state = _enter_from_idle(inp, levels)
    cur = level_by_name(levels, state.level)

    # avto dosegel cilj: brez moči več kot 5 min, kadar pavza ni naša
    waiting = cur.tier != TIER_PAUSED and (ch.status == STATUS_WAITING_CAR or ch.p_ev_kw < NO_POWER_KW)
    state = dataclasses.replace(state, ticks_waiting=state.ticks_waiting + 1 if waiting else 0)
    if state.ticks_waiting >= WAITING_TICKS:
        return out(None, TIER_IDLE, "idle_car_waiting", RegulatorState())

    # števci histereze
    state = dataclasses.replace(
        state,
        ticks_above_raise=state.ticks_above_raise + 1 if p_ev_allow >= p_tier + RAISE_MARGIN_KW else 0,
        ticks_below_lower=state.ticks_below_lower + 1 if p_ev_allow < p_tier - LOWER_MARGIN_KW else 0,
        ticks_above_resume=state.ticks_above_resume + 1 if p_ev_allow >= floor.power_kw + RESUME_MARGIN_KW else 0,
    )
    tier_age = inp.now - state.tier_since
    level_age = inp.now - state.level_since

    # korak 6: pavza in vrnitev
    if cur.tier == TIER_PAUSED:
        if tier_age < MIN_PAUSE:
            return out(cur, TIER_PAUSED, "pause_min_duration", state)
        if state.ticks_above_resume < RESUME_TICKS:
            return out(cur, TIER_PAUSED, "resume_pending", state)
        new = highest_in_tier(levels, TIER_LOW, p_ev_allow)
        return out(new, TIER_LOW, "resume_from_pause", _switched(state, new, inp.now, new_tier=True))
    if p_proj_floor > tariff.agreed_kw:
        new = level_by_name(levels, LEVEL_OFF)
        return out(new, TIER_PAUSED, "pause_window_projection", _switched(state, new, inp.now, new_tier=True))

    # korak 5 in 7: raven high
    if cur.tier == TIER_HIGH:
        if cand.tier == TIER_LOW:
            if state.hard_threshold:
                return out(cand, TIER_LOW, "lower_hard_threshold", _switched(state, cand, inp.now, new_tier=True))
            if state.ticks_below_lower >= LOWER_TICKS:
                return out(cand, TIER_LOW, "lower_after_hysteresis", _switched(state, cand, inp.now, new_tier=True))
            wb_floor = highest_in_tier(levels, TIER_HIGH, 0.0)
            reason = "lower_pending" if state.ticks_below_lower else "high_floor"
            return out(wb_floor, TIER_HIGH, reason, _switched(state, wb_floor, inp.now))
        # korak 7: zvezni kandidatni tok, sprememba samo pri razliki 1 A ali več
        highs = [lv for lv in levels if lv.tier == TIER_HIGH]
        i_cand = min(max(p_ev_allow / kw_per_amp, highs[0].wb_current), highs[-1].wb_current)
        if abs(i_cand - cur.wb_current) < HIGH_DEADBAND_A:
            return out(cur, TIER_HIGH, "steady", state)
        target_a = min(int(i_cand), cur.wb_current + HIGH_STEP_UP_A)
        new = level_by_name(levels, _wb_level_name(levels, target_a))
        if new == cur:
            return out(cur, TIER_HIGH, "steady", state)
        return out(new, TIER_HIGH, "high_adjust", _switched(state, new, inp.now))

    # korak 4 in 8: raven low
    if cand.tier == TIER_HIGH:
        if state.ticks_above_raise >= RAISE_TICKS and tier_age >= MIN_LOW_AGE_FOR_RAISE:
            return out(cand, TIER_HIGH, "raise_to_high", _switched(state, cand, inp.now, new_tier=True))
        new = highest_in_tier(levels, TIER_LOW, p_ev_allow)
        reason = "raise_pending"
    else:
        new = cand
        reason = "low_adjust"
    if new == cur:
        return out(cur, TIER_LOW, "steady" if reason == "low_adjust" else reason, state)
    if level_age < LOW_HOLD:
        return out(cur, TIER_LOW, "low_hold", state)
    return out(new, TIER_LOW, reason, _switched(state, new, inp.now))


# ----------------------------------------------------------------------
# pomožne
# ----------------------------------------------------------------------
def _idle_reason(inp: Inputs, state: RegulatorState) -> str | None:
    if inp.mode == MODE_OFF:
        return "idle_mode_off"
    if not inp.charger.cable_connected:
        return "idle_no_cable"
    if state.level != LEVEL_OFF and inp.charger.status == STATUS_PAUSED:
        return "idle_paused_externally"
    return None


def _enter_from_idle(inp: Inputs, levels: list[Level]) -> RegulatorState:
    """Raven se ugotovi iz P_ev in toka wallboxa (spec 6.6). Avto, ki še ni začel, je na Max (6.5)."""
    ch = inp.charger
    highs = [lv for lv in levels if lv.tier == TIER_HIGH]
    wb_a = min(max(ch.wb_current, highs[0].wb_current), highs[-1].wb_current)
    wb_level = level_by_name(levels, _wb_level_name(levels, wb_a))
    if ch.p_ev_kw < STARTING_P_EV_KW or abs(ch.p_ev_kw - wb_level.power_kw) <= CONFIRM_BAND_KW:
        level = wb_level
    else:
        lows = [lv for lv in levels if lv.tier == TIER_LOW and lv.car_limit == ch.car_limit]
        level = lows[0] if lows else lowest_charging_level(levels)
    return RegulatorState(level=level.name, tier_since=inp.now, level_since=inp.now)


def _switched(state: RegulatorState, new: Level, now: datetime.datetime, new_tier: bool = False) -> RegulatorState:
    return dataclasses.replace(
        state,
        level=new.name,
        level_since=now,
        tier_since=now if new_tier else state.tier_since,
        ticks_above_raise=0 if new_tier else state.ticks_above_raise,
        ticks_below_lower=0 if new_tier else state.ticks_below_lower,
        ticks_above_resume=0 if new_tier else state.ticks_above_resume,
    )


def _wb_level_name(levels: list[Level], amps: int) -> str:
    for lv in levels:
        if lv.tier == TIER_HIGH and lv.wb_current == amps:
            return lv.name
    raise KeyError(amps)


def _kw_per_amp(levels: list[Level]) -> float:
    lv = min((lv for lv in levels if lv.tier == TIER_HIGH), key=lambda lv: lv.wb_current)
    return lv.power_kw / lv.wb_current
