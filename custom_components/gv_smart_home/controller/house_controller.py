# custom_components/gv_smart_home/controller/house_controller.py
from __future__ import annotations

import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from ..const import HC_WINDOW_MINUTES


class HouseController:
    """
    Stores raw grid power samples and computes average over a window.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.samples: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # SAMPLE MGMT
    # ------------------------------------------------------------------
    def add_sample(self, sample: dict[str, Any]) -> None:
        self.samples.append(sample)

        cutoff = datetime.datetime.now() - datetime.timedelta(
            minutes=HC_WINDOW_MINUTES
        )

        self.samples = [
            s
            for s in self.samples
            if s.get("ts") and s["ts"] >= cutoff
        ]

    def get_latest_sample(self) -> dict[str, Any] | None:
        if not self.samples:
            return None
        return self.samples[-1]

    # ------------------------------------------------------------------
    # CALCULATIONS
    # ------------------------------------------------------------------
    def compute_average_grid_power(self) -> float | None:
        if not self.samples:
            return None

        cutoff = datetime.datetime.now() - datetime.timedelta(
            minutes=HC_WINDOW_MINUTES
        )

        values = [
            float(s["grid_power_w"])
            for s in self.samples
            if s.get("ts")
            and s.get("grid_power_w") is not None
            and s["ts"] >= cutoff
        ]

        if not values:
            return None

        return round(sum(values) / len(values))
