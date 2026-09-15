"""Varovalka po fazah (spec 6.1, 6.2a) na primeru E iz poglavja 7."""

import pytest

from core.fuse import (
    DEFAULT_VOLTAGE,
    PhaseCurrents,
    fuse_limit_a,
    headroom_a,
    house_currents_a,
    over_fuse_limit,
    phase_currents_a,
)

FUSE, MARGIN = 20.0, 3.0


def test_phase_currents_from_power_and_voltage_import_only():
    # predznak števca: pozitivno oddaja, negativno uvoz; tok je samo za uvoz
    i = phase_currents_a(PhaseCurrents.from_power_w((-2300.0, 0.0, 460.0), (230.0, 230.0, 230.0)))
    assert i == pytest.approx((10.0, 0.0, 0.0))


def test_missing_voltage_falls_back_to_230():
    p = PhaseCurrents.from_power_w((-2300.0, -2300.0, -2300.0), (None, 0.0, 240.0))
    assert p.voltage_v == (DEFAULT_VOLTAGE, DEFAULT_VOLTAGE, 240.0)


def test_house_currents_subtract_car():
    p = PhaseCurrents.from_power_w((-2300.0, -4600.0, -2300.0), (230.0,) * 3)
    assert house_currents_a(p, i_ev_a=7.0) == pytest.approx((3.0, 13.0, 3.0))


def test_headroom_is_worst_phase_and_capped_when_exporting():
    assert fuse_limit_a(FUSE, MARGIN) == 17.0
    assert headroom_a((3.0, 13.0, 3.0), FUSE, MARGIN) == 4.0
    # oddaja na vseh fazah: hiša negativna, prostor ostane na robu (spec 6.6)
    assert headroom_a((-5.0, -5.0, -5.0), FUSE, MARGIN) == 17.0


def test_E_oven_on_phase_b_with_car_at_10A():
    # hiša 1 kW enakomerno, pečica 3 kW na fazi B, avto 10 A na fazo
    house_w = 1000.0 / 3
    car_w = 10.0 * 230.0
    p = PhaseCurrents.from_power_w((-(house_w + car_w), -(house_w + 3000.0 + car_w), -(house_w + car_w)), (230.0,) * 3)
    i = phase_currents_a(p)
    assert i[1] == pytest.approx(24.5, abs=0.1)
    assert over_fuse_limit(p, FUSE, MARGIN)

    # trdi prag: wallbox na 6 A, faza B še vedno nad rob
    car_w = 6.0 * 230.0
    p6 = PhaseCurrents.from_power_w((-(house_w + car_w), -(house_w + 3000.0 + car_w), -(house_w + car_w)), (230.0,) * 3)
    assert phase_currents_a(p6)[1] == pytest.approx(20.5, abs=0.1)
    assert over_fuse_limit(p6, FUSE, MARGIN)

    house = house_currents_a(p6, i_ev_a=6.0)
    assert house[1] == pytest.approx(14.5, abs=0.1)
    assert headroom_a(house, FUSE, MARGIN) == pytest.approx(2.5, abs=0.1)
    assert headroom_a(house, FUSE, MARGIN) * 0.69 < 2.0  # tarifa bi dala 4 kW, varovalka car_6A


def test_not_over_limit_when_all_phases_under_margin():
    p = PhaseCurrents.from_power_w((-3900.0, -3900.0, -3900.0), (230.0,) * 3)  # 17 A točno
    assert not over_fuse_limit(p, FUSE, MARGIN)
