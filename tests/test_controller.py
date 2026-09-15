"""Controller: vzorci števca in kontrolni tick brez HA (spec 5 in 6.4)."""

import datetime

import pytest

from core.controller import Config, Controller
from core.fuse import PhaseCurrents
from core.models import MODE_TARIFF, STATUS_CHARGING, ChargerState

# 2026-09-14 je ponedeljek v nizki sezoni: 22h je osnovni blok 3 + 1 = blok 4
T0 = datetime.datetime(2026, 9, 14, 22, 0, 0)
CFG = Config(block_power_kw={1: 5.4, 2: 7.1, 3: 10.0, 4: 10.0, 5: 10.0})


def at(seconds: float) -> datetime.datetime:
    return T0 + datetime.timedelta(seconds=seconds)


def phases(import_kw: tuple[float, float, float]) -> PhaseCurrents:
    return PhaseCurrents(import_kw, (230.0, 230.0, 230.0))


def even(total_import_kw: float) -> PhaseCurrents:
    return phases((total_import_kw / 3,) * 3)


def charging(p_ev: float, wb: int, limit: str = "Max") -> ChargerState:
    return ChargerState(True, STATUS_CHARGING, p_ev, wb, limit)


def test_tariff_from_calendar_and_config():
    c = Controller(CFG, T0)
    t = c.tariff_at(T0)
    assert t.block == 4 and t.agreed_kw == 10.0 and t.target_kw == 8.0
    assert c.tariff_at(datetime.datetime(2026, 9, 14, 10, 0)).block == 2


def test_meter_sample_feeds_window_other_and_headroom():
    c = Controller(CFG, T0)
    # hiša 1,2 kW, avto 6,2 kW (wb_9A): uvoz 7,4, P_other 1,2
    c.on_meter(at(0), p_grid_kw=-7.4, phases=even(7.4), p_ev_kw=6.2, i_ev_a=9.0)
    c.on_meter(at(10), p_grid_kw=-7.4, phases=even(7.4), p_ev_kw=6.2, i_ev_a=9.0)
    assert c.p_other_used_kw == pytest.approx(1.2)
    assert c.window.energy_kwmin == pytest.approx(7.4 * 10 / 60)
    # 7,4 kW / 3 faz / 230 V = 10,7 A na fazo, brez avta 1,7 A, prostor 15,3 A
    assert c.i_headroom_a == pytest.approx(17.0 - (7.4 / 3 * 1000 / 230 - 9.0))


def test_other_power_drops_with_delay():
    c = Controller(CFG, T0)
    for s in range(0, 130, 10):
        c.on_meter(at(s), -7.4, even(7.4), 6.2, 9.0)
    c.on_meter(at(130), -6.5, even(6.5), 6.2, 9.0)  # črpalka izklop, hiša 0,3
    assert c.p_other_used_kw > 1.0
    for s in range(140, 270, 10):
        c.on_meter(at(s), -6.5, even(6.5), 6.2, 9.0)
    assert c.p_other_used_kw == pytest.approx(0.3, abs=0.01)


def test_tick_example_A():
    c = Controller(CFG, T0)
    c.on_meter(at(0), -7.4, even(7.4), 6.2, 9.0)
    d = c.tick(at(0), charging(6.2, 9), MODE_TARIFF)
    assert d.level == "wb_9A"  # vstop iz idle: P_ev 6,2 je v pasu wb_9A
    assert d.p_ev_allow_kw == pytest.approx(6.8)


def test_hard_threshold_on_import_over_agreed_lowers_next_tick():
    c = Controller(CFG, T0)
    c.on_meter(at(0), -7.9, even(7.9), 6.9, 10.0)
    c.tick(at(0), charging(6.9, 10), MODE_TARIFF)
    for s in range(10, 720, 10):
        assert not c.on_meter(at(s), -7.9, even(7.9), 6.9, 10.0)
    # pečica: uvoz 12,4 > 10
    assert c.on_meter(at(720), -12.4, even(12.4), 6.9, 10.0) is True
    assert c.state.level == "wb_6A" and c.state.hard_threshold
    d = c.tick(at(720), charging(4.1, 6), MODE_TARIFF)
    assert d.level == "car_8A" and d.reason == "lower_hard_threshold"


def test_hard_threshold_on_single_phase_over_fuse_limit():
    c = Controller(CFG, T0)
    c.on_meter(at(0), -7.9, even(7.9), 6.9, 10.0)
    c.tick(at(0), charging(6.9, 10), MODE_TARIFF)
    # faza B 24,5 A (5,63 kW), skupni uvoz pod 10 kW
    assert c.on_meter(at(10), -9.2, phases((2.63, 5.63, 2.63)), 6.9, 10.0) is True
    assert c.state.level == "wb_6A"


def test_tick_before_any_meter_sample_uses_zero_other_and_full_headroom():
    c = Controller(CFG, T0)
    d = c.tick(at(0), charging(0.0, 6), MODE_TARIFF)
    assert d.p_ev_allow_kw == pytest.approx(8.0)
    assert d.level == "wb_8A"
