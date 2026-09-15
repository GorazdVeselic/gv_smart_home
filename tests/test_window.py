import datetime

import pytest

from core.window import WindowBudget, window_start

T0 = datetime.datetime(2026, 9, 14, 22, 0, 0)


def at(minutes: float, seconds: float = 0) -> datetime.datetime:
    return T0 + datetime.timedelta(minutes=minutes, seconds=seconds)


def test_window_start_aligns_to_quarter():
    assert window_start(datetime.datetime(2026, 9, 14, 22, 7, 31)) == datetime.datetime(2026, 9, 14, 22, 0)
    assert window_start(datetime.datetime(2026, 9, 14, 22, 44, 59)) == datetime.datetime(2026, 9, 14, 22, 30)


def test_constant_import_gives_same_average():
    w = WindowBudget(at(0))
    for m in range(0, 15):
        w.add_sample(at(m), 8.0)
    assert w.average_so_far(at(14)) == pytest.approx(8.0)
    assert w.energy_kwmin == pytest.approx(8.0 * 14)


def test_previous_value_holds_until_next_sample():
    w = WindowBudget(at(0))
    w.add_sample(at(0), 4.0)
    w.add_sample(at(10), 12.0)  # 4 kW je veljalo 10 min
    assert w.energy_kwmin == pytest.approx(40.0)
    w.add_sample(at(12), 0.0)  # 12 kW je veljalo 2 min
    assert w.energy_kwmin == pytest.approx(64.0)


def test_negative_import_is_clamped_to_zero():
    w = WindowBudget(at(0))
    w.add_sample(at(0), -3.0)
    w.add_sample(at(5), -3.0)
    assert w.energy_kwmin == 0.0


def test_rollover_closes_window_and_starts_new():
    w = WindowBudget(at(0))
    w.add_sample(at(0), 6.0, agreed_kw=5.4)
    w.add_sample(at(14), 6.0, agreed_kw=5.4)
    w.add_sample(at(16), 2.0, agreed_kw=5.4)  # čez mejo 22:15
    assert w.last_window is not None
    assert w.last_window.average_kw == pytest.approx(6.0)
    assert w.last_window.exceeded is True
    assert w.start == at(15)
    assert w.energy_kwmin == pytest.approx(6.0 * 1)  # 6 kW je veljalo od 22:15 do 22:16


def test_window_closes_with_agreed_power_of_its_own_block():
    # 22:45 do 23:00 je še v prejšnjem bloku (10 kW), ob 23:00 pride blok s 5,4 kW
    w = WindowBudget(at(45))
    w.add_sample(at(45), 8.0, agreed_kw=10.0)
    w.add_sample(at(59), 8.0, agreed_kw=10.0)
    w.add_sample(at(60), 8.0, agreed_kw=5.4)
    assert w.last_window.agreed_kw == 10.0
    assert w.last_window.exceeded is False


def test_allowed_import_full_budget_at_window_start():
    w = WindowBudget(at(0))
    w.add_sample(at(0), 0.0)
    assert w.allowed_import_kw(at(0), target_kw=8.0, agreed_kw=10.0) == pytest.approx(8.0)
    # sekundo kasneje brez uvoza je proračun malenkost večji, a še vedno pod dogovorjeno
    assert 8.0 < w.allowed_import_kw(at(0, 1), target_kw=8.0, agreed_kw=10.0) < 8.02


def test_allowed_import_after_high_usage_is_lower_and_capped():
    # primer D iz speca: 12 min po 7,9 kW, cilj 8,0, dogovorjeno 10
    w = WindowBudget(at(0))
    w.add_sample(at(0), 7.9)
    w.add_sample(at(12), 7.9)
    assert w.energy_kwmin == pytest.approx(94.8)
    allow = w.allowed_import_kw(at(12), target_kw=8.0, agreed_kw=10.0)
    assert allow == pytest.approx((120 - 94.8) / 3)
    # rezerva porabljena: proračun bi dovolil več od dogovorjene moči, a je omejen
    w2 = WindowBudget(at(0))
    w2.add_sample(at(0), 2.0)
    w2.add_sample(at(12), 2.0)
    assert w2.allowed_import_kw(at(12), target_kw=8.0, agreed_kw=10.0) == 10.0


def test_allowed_import_last_minute_uses_target():
    w = WindowBudget(at(0))
    w.add_sample(at(0), 0.0)
    w.add_sample(at(14, 30), 0.0)
    assert w.allowed_import_kw(at(14, 30), target_kw=8.0, agreed_kw=10.0) == 8.0


def test_projected_average():
    w = WindowBudget(at(0))
    w.add_sample(at(0), 7.9)
    w.add_sample(at(12), 7.9)
    assert w.projected_average_kw(at(12), 12.9) == pytest.approx((94.8 + 3 * 12.9) / 15)
    assert w.projected_average_kw(at(12), -1.0) == pytest.approx(94.8 / 15)


def test_restore_estimate_mid_window():
    w = WindowBudget(at(7))
    w.restore_estimate(at(7), 5.0)
    assert w.start == at(0)
    assert w.energy_kwmin == pytest.approx(35.0)
    w.add_sample(at(8), 5.0)
    assert w.energy_kwmin == pytest.approx(40.0)


def test_time_going_backwards_resets():
    w = WindowBudget(at(0))
    w.add_sample(at(5), 5.0)
    w.add_sample(at(10), 5.0)
    w.add_sample(at(3), 5.0)
    assert w.energy_kwmin == 0.0
