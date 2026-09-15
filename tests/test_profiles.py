"""Sintetični in izmerjeni profil za simulacijo."""

import datetime

import pytest

from sim.profiles import MeasuredProfile, house_kw, pv_kw


def test_synthetic_house_has_pump_and_oven_on_phase_b():
    quiet = house_kw(datetime.datetime(2026, 9, 15, 3, 0))
    assert sum(quiet) == pytest.approx(0.5)
    pump = house_kw(datetime.datetime(2026, 9, 15, 3, 25))
    assert sum(pump) == pytest.approx(3.0)
    oven = house_kw(datetime.datetime(2026, 9, 15, 18, 5))
    assert oven[1] - oven[0] == pytest.approx(3.0)


def test_synthetic_pv_is_zero_at_night_and_peaks_at_noon():
    assert pv_kw(datetime.datetime(2026, 9, 15, 2, 0), "clear") == 0.0
    assert pv_kw(datetime.datetime(2026, 9, 15, 13, 0), "clear") == pytest.approx(6.0)
    assert pv_kw(datetime.datetime(2026, 9, 15, 17, 0), "winter") == 0.0


def test_measured_profile_maps_by_time_of_day(tmp_path):
    p = tmp_path / "p.csv"
    p.write_text(
        "time,house_a_kw,house_b_kw,house_c_kw,pv_kw,ev_kw\n"
        "2026-09-14T22:00:00+02:00,0.1,0.2,-0.01,0.0,1.6\n"
        "2026-09-14T22:00:10+02:00,0.1,0.9,0.0,0.0,1.6\n"
        "2026-09-15T10:00:00+02:00,0.05,0.2,0.05,4.3,0.0\n"
    )
    prof = MeasuredProfile(p)
    assert prof.house_kw(datetime.datetime(2026, 12, 8, 22, 0, 3)) == (0.1, 0.2, 0.0)  # negativno se odreže
    assert prof.house_kw(datetime.datetime(2026, 12, 8, 22, 0, 15))[1] == 0.9
    assert prof.pv_kw(datetime.datetime(2026, 12, 8, 10, 0, 0)) == 4.3
    # manjkajoč čas: najbližji zapis
    assert prof.pv_kw(datetime.datetime(2026, 12, 8, 9, 59, 0)) == 4.3
