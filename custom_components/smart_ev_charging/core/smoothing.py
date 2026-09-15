"""Glajenje po specu 6.1: `max(povprečje zadnjih 2 minut, trenutna vrednost)`.

Skok navzgor deluje takoj, padec pride z zamikom okna. Povprečje je časovno
uteženo, prejšnja vrednost velja do naslednjega vzorca (kot v WindowBudget).
Uporaba: P_other_used in I_house_x.
"""

from __future__ import annotations

import datetime
from collections import deque


class RiseFastFallSlow:
    def __init__(self, window: datetime.timedelta) -> None:
        self._window = window
        self._samples: deque[tuple[datetime.datetime, float]] = deque()

    def update(self, now: datetime.datetime, value: float) -> float:
        if self._samples and now < self._samples[-1][0]:
            self._samples.clear()
        self._samples.append((now, value))
        cutoff = now - self._window
        # obdrži vzorec, ki sega čez začetek okna, ostale starejše zavrzi
        while len(self._samples) >= 2 and self._samples[1][0] <= cutoff:
            self._samples.popleft()
        return max(self._average(cutoff), value)

    def _average(self, cutoff: datetime.datetime) -> float:
        total = 0.0
        weighted = 0.0
        for (t0, v), (t1, _) in zip(self._samples, list(self._samples)[1:]):
            w = (t1 - max(t0, cutoff)).total_seconds()
            if w > 0:
                total += w
                weighted += v * w
        return weighted / total if total > 0 else self._samples[-1][1]
