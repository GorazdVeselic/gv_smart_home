"""Glajenje po specu 6.1: skok navzgor takoj, padec z 2-minutnim zamikom."""

import datetime

import pytest

from core.smoothing import RiseFastFallSlow

T0 = datetime.datetime(2026, 9, 14, 22, 0, 0)


def at(seconds: float) -> datetime.datetime:
    return T0 + datetime.timedelta(seconds=seconds)


def test_first_sample_is_returned_as_is():
    s = RiseFastFallSlow(window=datetime.timedelta(minutes=2))
    assert s.update(at(0), 1.2) == 1.2


def test_jump_up_acts_immediately():
    s = RiseFastFallSlow(window=datetime.timedelta(minutes=2))
    s.update(at(0), 0.3)
    s.update(at(10), 0.3)
    assert s.update(at(20), 5.5) == 5.5


def test_drop_is_held_by_two_minute_average():
    s = RiseFastFallSlow(window=datetime.timedelta(minutes=2))
    for t in range(0, 130, 10):
        s.update(at(t), 1.2)
    # črpalka se izklopi: povprečje zadnjih 2 min drži vrednost nad trenutno
    v = s.update(at(130), 0.3)
    assert 0.3 < v <= 1.2
    for t in range(140, 260, 10):
        v = s.update(at(t), 0.3)
    assert v == pytest.approx(0.3, abs=0.01)


def test_drop_decays_monotonically():
    s = RiseFastFallSlow(window=datetime.timedelta(minutes=2))
    for t in range(0, 130, 10):
        s.update(at(t), 4.0)
    values = [s.update(at(t), 0.3) for t in range(130, 260, 10)]
    assert values == sorted(values, reverse=True)
    assert values[0] > 3.0 and values[-1] == pytest.approx(0.3, abs=0.01)


def test_time_going_backwards_resets():
    s = RiseFastFallSlow(window=datetime.timedelta(minutes=2))
    s.update(at(0), 4.0)
    s.update(at(60), 4.0)
    assert s.update(at(30), 0.3) == 0.3
