"""Zaporedja ukazov (spec 6.5, 6.6): načrt, potrditve, ponovni poskus, tapering, omejitev."""

import datetime

import pytest

from core.levels import build_levels
from core.models import STATUS_CHARGING, STATUS_PAUSED, STATUS_WAITING_CAR, Decision, RegulatorState
from core.sequences import (
    CMD_CAR_LIMIT,
    CMD_CAR_START,
    CMD_WAIT,
    CMD_WB_CURRENT,
    CMD_WB_ENABLE,
    AdapterCore,
    Observation,
    plan_transition,
)

T0 = datetime.datetime(2026, 9, 14, 22, 0, 0)
LEVELS = build_levels()


def at(seconds: float) -> datetime.datetime:
    return T0 + datetime.timedelta(seconds=seconds)


def lv(name):
    return next(l for l in LEVELS if l.name == name)


def decision(level, reason="test"):
    return Decision(level=level, tier="", reason=reason, p_allow_kw=0, p_ev_allow_kw=0, candidate="", state=RegulatorState())


def obs(wb=6, status=STATUS_CHARGING, p_ev=0.0):
    return Observation(wb_current=wb, wb_status=status, p_ev_kw=p_ev)


# ----------------------------------------------------------------------
# načrt
# ----------------------------------------------------------------------
def test_plan_pause_is_one_local_command():
    kind, steps = plan_transition(lv("wb_9A"), lv("off"), LEVELS)
    assert kind == "pause"
    assert [s.cmd for s in steps] == [CMD_WB_ENABLE] and steps[0].value is False


def test_plan_resume_limit_wait_enable_start():
    kind, steps = plan_transition(lv("off"), lv("car_8A"), LEVELS)
    assert kind == "resume"
    assert [(s.cmd, s.value) for s in steps] == [(CMD_CAR_LIMIT, "8A"), (CMD_WAIT, 20), (CMD_WB_ENABLE, True), (CMD_CAR_START, True)]


def test_plan_lower_sets_wallbox_floor_then_car_limit():
    kind, steps = plan_transition(lv("wb_10A"), lv("car_6A"), LEVELS)
    assert kind == "lower"
    assert [(s.cmd, s.value) for s in steps] == [(CMD_WB_CURRENT, 6), (CMD_CAR_LIMIT, "6A")]
    assert steps[1].expected_kw == 1.6


def test_plan_raise_sets_wallbox_then_car_max():
    kind, steps = plan_transition(lv("car_8A"), lv("wb_11A"), LEVELS)
    assert kind == "raise"
    assert [(s.cmd, s.value) for s in steps] == [(CMD_WB_CURRENT, 11), (CMD_CAR_LIMIT, "Max")]
    assert steps[1].expected_kw == pytest.approx(7.59)


def test_plan_within_high_is_local_and_within_low_is_cloud():
    assert [s.cmd for s in plan_transition(lv("wb_9A"), lv("wb_11A"), LEVELS)[1]] == [CMD_WB_CURRENT]
    assert [s.cmd for s in plan_transition(lv("car_6A"), lv("car_8A"), LEVELS)[1]] == [CMD_CAR_LIMIT]


def test_plan_from_unknown_level_treats_as_high_entry():
    kind, steps = plan_transition(None, lv("car_8A"), LEVELS)
    assert kind == "lower"


# ----------------------------------------------------------------------
# izvajanje
# ----------------------------------------------------------------------
def test_lower_sequence_confirms_via_p_ev_band():
    a = AdapterCore(LEVELS)
    a.level = "wb_10A"
    sent = a.apply(decision("car_8A"), at(0), obs(wb=10, p_ev=6.9))
    assert [(s.cmd, s.value) for s in sent] == [(CMD_WB_CURRENT, 6)]
    assert a.busy and a.level == "car_8A"
    # wallbox potrdi po 2 s, nato gre meja avta
    sent = a.advance(at(2), obs(wb=6, p_ev=4.1))
    assert [(s.cmd, s.value) for s in sent] == [(CMD_CAR_LIMIT, "8A")]
    assert a.advance(at(10), obs(wb=6, p_ev=4.1)) == []
    assert a.busy
    # avto potrdi z močjo v pasu
    assert a.advance(at(20), obs(wb=6, p_ev=2.1)) == []
    assert not a.busy and a.last_command == ("car_limit", "8A", "confirmed")


def test_cloud_command_retries_once_then_times_out():
    a = AdapterCore(LEVELS)
    a.level = "car_6A"
    sent = a.apply(decision("car_8A"), at(0), obs(wb=6, p_ev=1.6))
    assert [s.cmd for s in sent] == [CMD_CAR_LIMIT]
    # avto vleče še vedno 4,1 (meja ni prijela): po 40 s ponovni poskus
    assert a.advance(at(39), obs(wb=6, p_ev=4.1)) == []
    sent = a.advance(at(40), obs(wb=6, p_ev=4.1))
    assert [s.cmd for s in sent] == [CMD_CAR_LIMIT]
    assert a.advance(at(80), obs(wb=6, p_ev=4.1)) == []
    assert not a.busy and a.timeouts == 1
    assert a.last_command == ("car_limit", "8A", "timeout")


def test_tapering_is_not_a_failure():
    # avto proti polni bateriji vleče manj od pričakovanega: brez ponovnega poskusa
    a = AdapterCore(LEVELS)
    a.level = "car_6A"
    a.apply(decision("car_8A"), at(0), obs(wb=6, p_ev=1.6))
    assert a.advance(at(40), obs(wb=6, status=STATUS_CHARGING, p_ev=1.0)) == []
    assert not a.busy and a.timeouts == 0
    assert a.last_command == ("car_limit", "8A", "tapering")


def test_resume_sequence_waits_20s_then_enables_and_starts():
    a = AdapterCore(LEVELS)
    a.level = "off"
    sent = a.apply(decision("car_8A"), at(0), obs(wb=6, status=STATUS_PAUSED))
    assert [(s.cmd, s.value) for s in sent] == [(CMD_CAR_LIMIT, "8A")]
    assert a.advance(at(19), obs(wb=6, status=STATUS_PAUSED)) == []
    sent = a.advance(at(20), obs(wb=6, status=STATUS_PAUSED))
    assert [(s.cmd, s.value) for s in sent] == [(CMD_WB_ENABLE, True)]
    sent = a.advance(at(22), obs(wb=6, status=STATUS_WAITING_CAR))
    assert [(s.cmd, s.value) for s in sent] == [(CMD_CAR_START, True)]
    assert a.advance(at(41), obs(wb=6, status=STATUS_CHARGING, p_ev=2.0)) == []
    assert not a.busy and a.last_command == ("car_start", True, "confirmed")


def test_pause_confirms_via_status():
    a = AdapterCore(LEVELS)
    a.level = "wb_9A"
    sent = a.apply(decision("off"), at(0), obs(wb=9, p_ev=6.2))
    assert [(s.cmd, s.value) for s in sent] == [(CMD_WB_ENABLE, False)]
    a.advance(at(2), obs(wb=9, status=STATUS_PAUSED, p_ev=0.0))
    assert not a.busy


def test_busy_adapter_skips_new_decisions():
    a = AdapterCore(LEVELS)
    a.level = "wb_10A"
    a.apply(decision("car_8A"), at(0), obs(wb=10, p_ev=6.9))
    assert a.apply(decision("car_6A"), at(5), obs(wb=6, p_ev=4.1)) == []
    assert a.skipped_busy == 1 and a.level == "car_8A"


def test_same_cloud_command_at_most_once_per_ten_minutes():
    a = AdapterCore(LEVELS)
    a.level = "car_6A"
    a.apply(decision("car_8A"), at(0), obs(wb=6, p_ev=1.6))
    a.advance(at(20), obs(wb=6, p_ev=2.0))
    a.level = "car_6A"  # ročno nazaj, motor spet hoče 8A
    assert a.apply(decision("car_8A"), at(300), obs(wb=6, p_ev=1.6)) == []
    assert a.rate_limited == 1 and a.level == "car_6A"
    sent = a.apply(decision("car_8A"), at(601), obs(wb=6, p_ev=1.6))
    assert [s.cmd for s in sent] == [CMD_CAR_LIMIT]


def test_hard_threshold_in_high_sends_wallbox_floor_even_when_busy():
    a = AdapterCore(LEVELS)
    a.level = "car_8A"
    a.apply(decision("wb_11A"), at(0), obs(wb=6, p_ev=2.0))  # dvig, zaporedje teče
    sent = a.hard_threshold(at(5))
    assert [(s.cmd, s.value) for s in sent] == [(CMD_WB_CURRENT, 6)]
    assert a.level == "wb_6A"
    a.level = "car_8A"
    assert a.hard_threshold(at(6)) == []


def test_idle_resets_wallbox_to_floor_and_cancels_sequence():
    a = AdapterCore(LEVELS)
    a.level = "car_8A"
    a.apply(decision("wb_11A"), at(0), obs(wb=6, p_ev=2.0))
    sent = a.apply(decision(None, "idle_no_cable"), at(5), obs(wb=11, p_ev=0.0))
    assert [(s.cmd, s.value) for s in sent] == [(CMD_WB_CURRENT, 6)]
    assert a.level is None and not a.busy
