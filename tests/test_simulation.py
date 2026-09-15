"""Simulacija dneva (spec 8): 4 dnevi, trditve o oknih, varovalki in oblačnih ukazih.

Profil hiše je sintetičen (sim/profiles.py) in ob 18:20 do 18:35 sam preseže rob
varovalke (pečica in črpalka na fazi B), zato je trditev o varovalki: preseganje,
ki bi ga dno car_6A odpravilo, ne traja več kot 30 s.
"""

import datetime

import pytest

from sim.run import DEFAULT_BLOCKS, Config, simulate

CFG = Config(block_power_kw=DEFAULT_BLOCKS, reserve_kw=2.0)

DAYS = [
    pytest.param(datetime.date(2026, 9, 15), "clear", id="september-delovni-jasno"),
    pytest.param(datetime.date(2026, 9, 12), "cloudy", id="september-sobota-oblacno"),
    pytest.param(datetime.date(2026, 12, 8), "winter", id="december-delovni"),
    pytest.param(datetime.date(2026, 12, 12), "winter", id="december-sobota"),
]


@pytest.fixture(scope="module")
def results():
    return {(d.values[0], d.values[1]): simulate(d.values[0], d.values[1], CFG) for d in DAYS}


@pytest.mark.parametrize("date,pv", DAYS)
def test_no_window_exceeds_agreed_power(results, date, pv):
    res = results[(date, pv)]
    assert len(res.windows) >= 95
    assert res.windows_over == []


@pytest.mark.parametrize("date,pv", DAYS)
def test_fuse_exceedance_the_car_could_fix_is_short(results, date, pv):
    res = results[(date, pv)]
    assert res.longest_over_fuse_avoidable_s <= 30


@pytest.mark.parametrize("date,pv", DAYS)
def test_no_timeouts_and_nothing_skipped(results, date, pv):
    res = results[(date, pv)]
    assert res.timeouts == 0 and res.rate_limited == 0
    assert res.charged_kwh > 50


@pytest.mark.parametrize("date,pv", DAYS[:2])
def test_cloud_commands_under_twelve_in_low_season(results, date, pv):
    assert results[(date, pv)].cloud_commands < 12


@pytest.mark.xfail(reason="odprto: pump vsako uro v bloku 1 preklaplja 8A/6A, glej spec 12", strict=True)
@pytest.mark.parametrize("date,pv", DAYS[2:])
def test_cloud_commands_under_twelve_in_high_season(results, date, pv):
    assert results[(date, pv)].cloud_commands < 12


def test_summary_reports_energy(results):
    for res in results.values():
        assert "napolnjeno" in res.summary()


def test_charge_anyway_never_pauses_and_still_respects_fuse():
    res = simulate(datetime.date(2026, 12, 8), "winter", CFG, charge_anyway=True)
    assert "pause_window_projection" not in res.reasons
    assert res.longest_over_fuse_avoidable_s <= 30
    base = simulate(datetime.date(2026, 12, 8), "winter", CFG)
    assert res.charged_kwh >= base.charged_kwh
