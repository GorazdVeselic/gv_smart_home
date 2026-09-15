"""Testi decide() po specu 6.4 in primeri A do E iz poglavja 7.

Tick je 30 s. Vsi primeri imajo rezervo 2 kW in faze enakomerno obremenjene
(headroom 17 A), razen primera E, ki preizkuša varovalko.
"""

import dataclasses
import datetime

import pytest

from core.decide import (
    LOWER_TICKS,
    RAISE_TICKS,
    RESUME_TICKS,
    WAITING_TICKS,
    decide,
    note_hard_threshold,
)
from core.levels import build_levels
from core.models import (
    MODE_OBSERVE,
    MODE_OFF,
    MODE_TARIFF,
    STATUS_CHARGING,
    STATUS_PAUSED,
    STATUS_WAITING_CAR,
    TIER_HIGH,
    TIER_IDLE,
    TIER_LOW,
    TIER_PAUSED,
    ChargerState,
    Inputs,
    RegulatorState,
    TariffState,
    WindowState,
)

T0 = datetime.datetime(2026, 9, 14, 22, 0, 0)
TICK = datetime.timedelta(seconds=30)
LEVELS = build_levels()

BLOCK1 = TariffState(block=1, agreed_kw=5.4, reserve_kw=2.0)
BLOCK2 = TariffState(block=2, agreed_kw=7.1, reserve_kw=2.0)
BLOCK3 = TariffState(block=3, agreed_kw=10.0, reserve_kw=2.0)
BLOCK4 = TariffState(block=4, agreed_kw=10.0, reserve_kw=2.0)


def inputs(
    *,
    now=T0,
    mode=MODE_TARIFF,
    tariff=BLOCK4,
    energy=0.0,
    remaining=15.0,
    cable=True,
    status=STATUS_CHARGING,
    p_ev=4.1,
    wb_current=6,
    car_limit="Max",
    p_other=1.0,
    headroom=17.0,
):
    return Inputs(
        now=now,
        mode=mode,
        tariff=tariff,
        window=WindowState(energy_kwmin=energy, remaining_min=remaining),
        charger=ChargerState(
            cable_connected=cable, status=status, p_ev_kw=p_ev, wb_current=wb_current, car_limit=car_limit
        ),
        p_other_used_kw=p_other,
        i_headroom_a=headroom,
    )


def state_at(level, now=T0, age_min=60.0):
    since = now - datetime.timedelta(minutes=age_min)
    return RegulatorState(level=level, tier_since=since, level_since=since)


def run_ticks(inp, state, n, start_now=None):
    """n tickov po 30 s, prvi ob start_now (privzeto inp.now). Vrne zadnjo odločitev."""
    now = start_now or inp.now
    d = None
    for _ in range(n):
        d = decide(inp.at(now), state, LEVELS)
        state = d.state
        now += TICK
    return d


# ----------------------------------------------------------------------
# primer A
# ----------------------------------------------------------------------
def test_A_night_block4_heat_pump_then_off():
    d = decide(inputs(p_other=1.2, p_ev=6.2, wb_current=9), state_at("wb_9A"), LEVELS)
    assert d.p_ev_allow_kw == pytest.approx(6.8)
    assert d.level == "wb_9A" and d.tier == TIER_HIGH

    d2 = decide(inputs(now=T0 + TICK, p_other=0.3, p_ev=6.2, wb_current=9), d.state, LEVELS)
    assert d2.p_ev_allow_kw == pytest.approx(7.7)
    assert d2.level == "wb_11A"


def test_high_deadband_ignores_changes_under_one_amp():
    # wb_11A: 7,5 kW da 10,87 A, razlika 0,13 A -> brez spremembe; 7,0 kW da 10,14 A, še vedno pod 1 A
    d = decide(inputs(p_other=0.5, p_ev=7.6, wb_current=11), state_at("wb_11A"), LEVELS)
    assert d.level == "wb_11A" and d.reason == "steady"
    d = decide(inputs(p_other=1.0, p_ev=7.6, wb_current=11), state_at("wb_11A"), LEVELS)
    assert d.level == "wb_11A" and d.reason == "steady"
    # 6,8 kW da 9,86 A, razlika 1,14 A -> wb_9A (navzdol brez omejitve)
    d = decide(inputs(p_other=1.2, p_ev=7.6, wb_current=11), state_at("wb_11A"), LEVELS)
    assert d.level == "wb_9A"


def test_high_ramps_up_two_amps_per_tick():
    inp = inputs(p_other=0.3)
    d = decide(inp, state_at("wb_6A"), LEVELS)
    assert d.level == "wb_8A"
    d = decide(inp.at(T0 + TICK), d.state, LEVELS)
    assert d.level == "wb_10A"
    d = decide(inp.at(T0 + 2 * TICK), d.state, LEVELS)
    assert d.level == "wb_11A"
    d = decide(inp.at(T0 + 3 * TICK), d.state, LEVELS)
    assert d.level == "wb_11A" and d.reason == "steady"


# ----------------------------------------------------------------------
# primer B
# ----------------------------------------------------------------------
def test_B_winter_workday_block1():
    d = decide(inputs(tariff=BLOCK1, p_other=1.0, p_ev=2.0, wb_current=8, car_limit="8A"), state_at("car_8A"), LEVELS)
    assert d.p_allow_kw == pytest.approx(3.4)
    assert d.p_ev_allow_kw == pytest.approx(2.4)
    assert d.level == "car_8A" and d.tier == TIER_LOW


# ----------------------------------------------------------------------
# primer C
# ----------------------------------------------------------------------
def test_C_sunny_saturday_block3_stays_high_when_cloud_comes():
    d = decide(inputs(tariff=BLOCK3, p_other=-5.0, p_ev=11.0, wb_current=16), state_at("wb_16A"), LEVELS)
    # tarifa bi dala 13,0, prostor na fazi je omejen na 17 A tudi ob oddaji (spec 6.6)
    assert d.p_ev_allow_kw == pytest.approx(17 * 0.69)
    assert d.level == "wb_16A"

    d2 = decide(inputs(now=T0 + TICK, tariff=BLOCK3, p_other=-1.5, p_ev=11.0, wb_current=16), d.state, LEVELS)
    assert d2.p_ev_allow_kw == pytest.approx(9.5)
    assert d2.level == "wb_13A" and d2.tier == TIER_HIGH


def test_C_winter_saturday_block2_full_day():
    # zjutraj: hiša 2, PV 0
    d = decide(inputs(tariff=BLOCK2, p_other=2.0, p_ev=2.0, wb_current=8, car_limit="8A"), state_at("car_8A"), LEVELS)
    assert d.p_ev_allow_kw == pytest.approx(3.1)
    assert d.level == "car_8A"

    # dopoldne: PV 3,5, hiša 1 -> 7,6 nad 4,64, dvig šele po 20 tickih
    sunny = inputs(tariff=BLOCK2, p_other=-2.5, p_ev=2.0, wb_current=8, car_limit="8A")
    d = run_ticks(sunny, d.state, RAISE_TICKS - 1, start_now=T0 + TICK)
    assert d.level == "car_8A" and d.reason == "raise_pending"
    d = decide(sunny.at(T0 + RAISE_TICKS * TICK), d.state, LEVELS)
    assert d.p_ev_allow_kw == pytest.approx(7.6)
    assert d.level == "wb_11A" and d.tier == TIER_HIGH and d.reason == "raise_to_high"

    # zvečer: PV 0, hiša 0,9 -> wb_6A
    evening = inputs(now=T0 + datetime.timedelta(hours=8), tariff=BLOCK2, p_other=0.9, p_ev=7.6, wb_current=11)
    d = decide(evening, d.state, LEVELS)
    assert d.p_ev_allow_kw == pytest.approx(4.2)
    assert d.level == "wb_6A"

    # črpalka: hiša 4,0 -> 1,1 pod 3,84 dva ticka -> car_6A
    pump = inputs(now=evening.now + TICK, tariff=BLOCK2, p_other=4.0, p_ev=4.1, wb_current=6)
    d = decide(pump, d.state, LEVELS)
    assert d.p_ev_allow_kw == pytest.approx(1.1)
    assert d.level == "wb_6A" and d.reason == "lower_pending"
    d = decide(pump.at(pump.now + TICK), d.state, LEVELS)
    assert d.level == "car_6A" and d.tier == TIER_LOW and d.reason == "lower_after_hysteresis"


def test_raise_counter_resets_when_one_tick_drops_below_threshold():
    sunny = inputs(tariff=BLOCK2, p_other=-2.5, p_ev=2.0, wb_current=8, car_limit="8A")
    d = run_ticks(sunny, state_at("car_8A"), RAISE_TICKS - 1)
    assert d.level == "car_8A"
    dip = decide(sunny.with_other(0.6).at(T0 + (RAISE_TICKS - 1) * TICK), d.state, LEVELS)  # 4,5 pod 4,64
    assert dip.level == "car_8A" and dip.state.ticks_above_raise == 0
    d = run_ticks(sunny, dip.state, RAISE_TICKS - 1, start_now=T0 + RAISE_TICKS * TICK)
    assert d.level == "car_8A"
    d = decide(sunny.at(T0 + (2 * RAISE_TICKS) * TICK), d.state, LEVELS)
    assert d.level == "wb_11A"


def test_raise_waits_for_ten_minutes_in_low_tier():
    # raven low je stara 0 min: 20 tickov je 9,5 min od prvega, dvig šele ob 10 min
    sunny = inputs(tariff=BLOCK2, p_other=-2.5, p_ev=2.0, wb_current=8, car_limit="8A")
    d = run_ticks(sunny, state_at("car_8A", age_min=0.0), RAISE_TICKS)
    assert d.level == "car_8A" and d.reason == "raise_pending"
    d = decide(sunny.at(T0 + RAISE_TICKS * TICK), d.state, LEVELS)
    assert d.level == "wb_11A"


# ----------------------------------------------------------------------
# primer D
# ----------------------------------------------------------------------
def test_D_oven_in_minute_12_hard_threshold_lowers_immediately():
    # 12 minut po 7,9 kW, nato pečica: hiša 5,5, trdi prag že sprožen
    st = note_hard_threshold(state_at("wb_10A"), LEVELS)
    assert st.level == "wb_6A" and st.hard_threshold

    d = decide(inputs(energy=94.8, remaining=3.0, p_other=5.5, p_ev=4.1, wb_current=6), st, LEVELS)
    assert d.p_allow_kw == pytest.approx((120 - 94.8) / 3)
    assert d.p_ev_allow_kw == pytest.approx((120 - 94.8) / 3 - 5.5)
    assert d.candidate == "car_8A"
    assert d.level == "car_8A" and d.reason == "lower_hard_threshold"
    assert not d.state.hard_threshold

    # novo okno: P_allow 8,0, P_ev_allow 2,5 -> car_8A ostane
    d2 = decide(inputs(now=T0 + datetime.timedelta(minutes=3), p_other=5.5, p_ev=2.0, wb_current=6, car_limit="8A"), d.state, LEVELS)
    assert d2.p_ev_allow_kw == pytest.approx(2.5)
    assert d2.level == "car_8A" and d2.reason == "steady"


def test_D_without_flag_waits_two_ticks():
    inp = inputs(energy=94.8, remaining=3.0, p_other=5.5, p_ev=6.9, wb_current=10)
    d = decide(inp, state_at("wb_10A"), LEVELS)
    assert d.level == "wb_6A" and d.reason == "lower_pending"
    d = decide(inp.at(T0 + TICK), d.state, LEVELS)
    assert d.level == "car_8A"
    assert LOWER_TICKS == 2


# ----------------------------------------------------------------------
# primer E
# ----------------------------------------------------------------------
def test_E_oven_on_one_phase_fuse_limits_below_tariff():
    st = note_hard_threshold(state_at("wb_10A"), LEVELS)
    d = decide(inputs(p_other=4.0, headroom=2.6, p_ev=4.1, wb_current=6), st, LEVELS)
    assert d.p_ev_allow_kw == pytest.approx(min(8.0 - 4.0, 2.6 * 0.69))
    assert d.candidate == "car_6A"
    assert d.level == "car_6A" and d.reason == "lower_hard_threshold"


def test_hard_threshold_in_low_tier_keeps_level_and_hold():
    st = note_hard_threshold(state_at("car_8A", age_min=3.0), LEVELS)
    assert st.level == "car_8A"
    # hiša 3,5: pri 8A bi okno dalo 5,5 > 5,4, pri 6A 5,1
    d = decide(inputs(tariff=BLOCK1, p_other=3.5, p_ev=2.0, wb_current=8, car_limit="8A"), st, LEVELS)
    assert d.candidate == "car_6A"
    assert d.level == "car_8A" and d.reason == "low_hold"


# ----------------------------------------------------------------------
# pavza in vrnitev
# ----------------------------------------------------------------------
def test_pause_when_projection_exceeds_agreed_even_at_car_6A():
    # blok 1: hiša 4,5 + 1,6 = 6,1 > 5,4
    d = decide(inputs(tariff=BLOCK1, p_other=4.5, p_ev=1.6, wb_current=8, car_limit="6A"), state_at("car_6A"), LEVELS)
    assert d.level == "off" and d.tier == TIER_PAUSED and d.reason == "pause_window_projection"


def test_pause_goes_directly_from_high():
    d = decide(inputs(tariff=BLOCK1, p_other=4.5, p_ev=4.1, wb_current=6), state_at("wb_6A"), LEVELS)
    assert d.level == "off" and d.tier == TIER_PAUSED


def test_pause_lasts_at_least_ten_minutes_then_resumes_after_ten_ticks():
    paused = decide(inputs(tariff=BLOCK1, p_other=4.5), state_at("car_6A"), LEVELS)
    ok = inputs(tariff=BLOCK1, p_other=1.0, p_ev=0.0, status=STATUS_PAUSED, wb_current=6)  # P_ev_allow 2,4
    over = inputs(tariff=BLOCK1, p_other=4.5, p_ev=0.0, status=STATUS_PAUSED, wb_current=6)

    # 9,5 min pavze, pogoj velja zadnjih 5 min: še vedno pavza, ticki pa se štejejo
    d = run_ticks(ok, paused.state, RESUME_TICKS, start_now=T0 + datetime.timedelta(minutes=5))
    assert d.level == "off" and d.reason == "pause_min_duration"
    assert d.state.ticks_above_resume == RESUME_TICKS

    # ob 10 min: vrnitev takoj, ker je pogoj veljal zadnjih 10 tickov
    t10 = T0 + datetime.timedelta(minutes=10)
    d = decide(ok.at(t10), d.state, LEVELS)
    assert d.level == "car_8A" and d.tier == TIER_LOW and d.reason == "resume_from_pause"
    assert d.state.tier_since == d.state.level_since == t10

    # druga pot: projekcija čez do 10. minute, nato 10 tickov od t10 naprej
    d = run_ticks(over, paused.state, 20, start_now=T0)
    assert d.level == "off" and d.state.ticks_above_resume == 0
    d = run_ticks(ok, d.state, RESUME_TICKS - 1, start_now=t10)
    assert d.level == "off" and d.reason == "resume_pending"
    d = decide(ok.at(t10 + (RESUME_TICKS - 1) * TICK), d.state, LEVELS)
    assert d.level == "car_8A" and d.reason == "resume_from_pause"


def test_resume_counter_resets_on_dip():
    paused = decide(inputs(tariff=BLOCK1, p_other=4.5), state_at("car_6A"), LEVELS)
    t10 = T0 + datetime.timedelta(minutes=10)
    ok = inputs(tariff=BLOCK1, p_other=1.0, p_ev=0.0, status=STATUS_PAUSED)
    d = run_ticks(ok, paused.state, RESUME_TICKS - 1, start_now=t10)
    d = decide(ok.with_other(1.5).at(t10 + (RESUME_TICKS - 1) * TICK), d.state, LEVELS)  # 1,9 pod 2,1
    assert d.level == "off" and d.state.ticks_above_resume == 0


def test_stays_paused_while_projection_still_over():
    paused = decide(inputs(tariff=BLOCK1, p_other=4.5), state_at("car_6A"), LEVELS)
    still = inputs(now=T0 + datetime.timedelta(minutes=12), tariff=BLOCK1, p_other=4.5, p_ev=0.0, status=STATUS_PAUSED)
    d = decide(still, paused.state, LEVELS)
    assert d.level == "off" and d.reason == "resume_pending"


# ----------------------------------------------------------------------
# raven low: zadrževanje 6A <-> 8A
# ----------------------------------------------------------------------
def test_low_tier_switch_needs_ten_minute_hold():
    inp = inputs(tariff=BLOCK1, p_other=1.0, p_ev=1.6, wb_current=8, car_limit="6A")
    d = decide(inp, state_at("car_6A", age_min=3.0), LEVELS)
    assert d.candidate == "car_8A"
    assert d.level == "car_6A" and d.reason == "low_hold"
    d = decide(inp.at(T0 + datetime.timedelta(minutes=7)), d.state, LEVELS)
    assert d.level == "car_8A" and d.reason == "low_adjust"
    assert d.state.level_since == T0 + datetime.timedelta(minutes=7)


def test_nothing_fits_gives_car_6A_not_off():
    d = decide(inputs(tariff=BLOCK1, p_other=3.5, p_ev=2.0, wb_current=8, car_limit="8A"), state_at("car_8A"), LEVELS)
    assert d.p_ev_allow_kw == pytest.approx(-0.1)
    assert d.candidate == "car_6A"
    assert d.level == "car_6A" and d.reason == "low_adjust"


def test_low_tier_keeps_8A_while_reserve_absorbs_the_load():
    # črpalka: P_ev_allow 0,9 pod 2,0, a pri 8A okno da 5,0 < 5,4 -> brez oblačnega ukaza
    d = decide(inputs(tariff=BLOCK1, p_other=2.5, p_ev=2.0, wb_current=8, car_limit="8A"), state_at("car_8A"), LEVELS)
    assert d.candidate == "car_6A"
    assert d.level == "car_8A" and d.reason == "low_reserve_absorbs"
    # dvig 6A -> 8A gre po P_ev_allow kot prej
    d = decide(inputs(tariff=BLOCK1, p_other=1.0, p_ev=1.6, wb_current=8, car_limit="6A"), state_at("car_6A"), LEVELS)
    assert d.level == "car_8A"


# ----------------------------------------------------------------------
# idle, načini, vstop iz idle
# ----------------------------------------------------------------------
def test_mode_off_is_idle_and_resets_state():
    st = dataclasses.replace(state_at("wb_9A"), ticks_above_raise=5, hard_threshold=True)
    d = decide(inputs(mode=MODE_OFF), st, LEVELS)
    assert d.level is None and d.tier == TIER_IDLE and d.reason == "idle_mode_off"
    assert d.state == RegulatorState()


def test_no_cable_is_idle():
    d = decide(inputs(cable=False), state_at("wb_9A"), LEVELS)
    assert d.tier == TIER_IDLE and d.reason == "idle_no_cable"
    assert d.state.level is None


def test_car_waiting_is_idle_after_five_minutes_unless_pause_is_ours():
    # med vrnitvijo iz pavze in ob priklopu avto začne šele po 20 do 40 s
    waiting = inputs(status=STATUS_WAITING_CAR, p_ev=0.0, wb_current=8, car_limit="8A")
    d = run_ticks(waiting, state_at("car_8A"), WAITING_TICKS - 1)
    assert d.tier == TIER_LOW and d.level == "car_8A"
    d = decide(waiting.at(T0 + (WAITING_TICKS - 1) * TICK), d.state, LEVELS)
    assert d.tier == TIER_IDLE and d.reason == "idle_car_waiting"
    assert d.state == RegulatorState()

    # brez moči ob statusu Charging (avto poln) šteje enako
    d = run_ticks(inputs(p_ev=0.0, wb_current=8, car_limit="8A"), state_at("car_8A"), WAITING_TICKS)
    assert d.tier == TIER_IDLE

    # med lastno pavzo je čakanje pričakovano
    paused = state_at("off", age_min=2.0)
    d = run_ticks(inputs(tariff=BLOCK1, status=STATUS_WAITING_CAR, p_ev=0.0, p_other=1.0), paused, WAITING_TICKS + 2)
    assert d.tier == TIER_PAUSED and d.reason == "pause_min_duration"


def test_no_adjustment_while_car_draws_no_power():
    d = decide(inputs(p_ev=0.0, wb_current=16, p_other=-5.0), state_at("wb_16A"), LEVELS)
    assert d.level == "wb_16A" and d.reason == "car_no_power" and d.state.ticks_waiting == 1
    d = decide(inputs(p_ev=0.0, wb_current=6, car_limit="8A", p_other=-5.0), state_at("car_8A"), LEVELS)
    assert d.level == "car_8A" and d.reason == "car_no_power"


def test_waiting_counter_resets_when_power_returns():
    waiting = inputs(status=STATUS_WAITING_CAR, p_ev=0.0, wb_current=8, car_limit="8A")
    d = run_ticks(waiting, state_at("car_8A"), WAITING_TICKS - 1)
    d = decide(inputs(p_ev=2.0, wb_current=8, car_limit="8A"), d.state, LEVELS)
    assert d.state.ticks_waiting == 0 and d.tier == TIER_LOW


def test_external_pause_is_idle():
    d = decide(inputs(status=STATUS_PAUSED, p_ev=0.0), state_at("car_8A"), LEVELS)
    assert d.tier == TIER_IDLE and d.reason == "idle_paused_externally"


def test_observe_mode_decides_like_tariff():
    d = decide(inputs(mode=MODE_OBSERVE, p_other=1.2, p_ev=6.2, wb_current=9), state_at("wb_9A"), LEVELS)
    assert d.level == "wb_9A" and d.tier == TIER_HIGH


def test_entering_from_idle_infers_high_when_car_on_max():
    # priklop kabla: avto začne na Max, wallbox stoji na 6 A
    d = decide(inputs(p_ev=4.1, wb_current=6, p_other=4.5), RegulatorState(), LEVELS)
    assert d.state.tier_since == T0
    assert d.candidate == "car_8A"
    assert d.level == "wb_6A" and d.reason == "lower_pending"
    d = decide(inputs(now=T0 + TICK, p_ev=4.1, wb_current=6, p_other=4.5), d.state, LEVELS)
    assert d.level == "car_8A"


def test_high_floor_between_thresholds_stays_wb_6A():
    # kandidat je v low (4,0 < 4,14), a ni pod 3,84: ostane wb_6A brez štetja
    d = run_ticks(inputs(p_ev=4.1, wb_current=6, p_other=4.0), state_at("wb_6A"), 5)
    assert d.level == "wb_6A" and d.reason == "high_floor"
    assert d.state.ticks_below_lower == 0


def test_decision_reports_previous_level_after_inference():
    d = decide(inputs(p_ev=1.6, wb_current=6, car_limit="6A", p_other=7.0), RegulatorState(), LEVELS)
    assert d.previous_level == "car_6A"
    d = decide(inputs(mode=MODE_OFF), RegulatorState(), LEVELS)
    assert d.previous_level is None


def test_idle_stays_idle_until_car_draws_power():
    # ob priklopu in po doseženem cilju SOC status ostane Charging, moči pa ni:
    # brez vstopa, sicer motor vsakih 5 min znova dviguje tok
    d = decide(inputs(p_ev=0.0, wb_current=6, p_other=0.3), RegulatorState(), LEVELS)
    assert d.tier == TIER_IDLE and d.reason == "idle_no_power" and d.state == RegulatorState()
    d = decide(inputs(p_ev=0.0, wb_current=6, status=STATUS_WAITING_CAR), RegulatorState(), LEVELS)
    assert d.tier == TIER_IDLE
    # avto začne: vstop v high na trenutnem toku wallboxa
    d = decide(inputs(p_ev=4.1, wb_current=6, p_other=0.3), RegulatorState(), LEVELS)
    assert d.tier == TIER_HIGH and d.level == "wb_8A"


def test_entering_from_idle_infers_low_from_car_limit():
    d = decide(inputs(p_ev=1.6, wb_current=8, car_limit="6A", p_other=7.0), RegulatorState(), LEVELS)
    assert d.tier == TIER_LOW and d.level == "car_6A"
    d = decide(inputs(p_ev=2.0, wb_current=6, car_limit="8A", p_other=7.0), RegulatorState(), LEVELS)
    assert d.tier == TIER_LOW and d.level == "car_8A"
