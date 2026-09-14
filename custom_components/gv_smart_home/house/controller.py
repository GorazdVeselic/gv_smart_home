# custom_components/gv_smart_home/house/house_controller.py
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from ..const import HC_WINDOW_MINUTES, HC_SAMPLE_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)

# How many samples fit into rolling window
MAX_SAMPLES = int((60 / HC_SAMPLE_INTERVAL_SECONDS) * HC_WINDOW_MINUTES)


class HouseController:
    """
    Stores raw house consumption samples:
      - {'ts': datetime, 'grid_power_w': int | None}
    Provides:
      - add_sample()
      - samples (read-only list)
      - compute_average(last N minutes)
    """

    def __init__(self) -> None:
        self._samples: list[dict] = []

    # -------------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------------
    def add_sample(self, sample: dict) -> None:
        """
        Add new house sample.
        Format example:
          {
            "ts": datetime.now(),
            "grid_power_w": 1234,
          }
        """
        self._samples.append(sample)

        # Rolling window: drop oldest
        if len(self._samples) > MAX_SAMPLES:
            self._samples.pop(0)

    @property
    def samples(self) -> list[dict]:
        """Return stored raw samples."""
        return self._samples

    def average_power(self, minutes: Optional[int] = None) -> Optional[int]:
        """
        Compute average grid power in the last N minutes.
        If minutes is None → use configured rolling window (HC_WINDOW_MINUTES).
        """
        if not self._samples:
            return None

        now = datetime.now()

        if minutes is None:
            minutes = HC_WINDOW_MINUTES

        cutoff = now - timedelta(minutes=minutes)

        values = [
            s["grid_power_w"]
            for s in self._samples
            if s.get("grid_power_w") is not None and s["ts"] >= cutoff
        ]

        if not values:
            return None

        return int(sum(values) / len(values))
