"""En push koordinator s posnetkom stanja (spec 5). Brez update_interval: engine ga polni."""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass, field

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class Snapshot:
    now: datetime.datetime
    mode: str
    # tarifa
    block: int
    agreed_kw: float
    reserve_kw: float
    target_kw: float
    tariff_attrs: dict = field(default_factory=dict)
    # števec in okno
    meter_ok: bool = False
    wallbox_ok: bool = False
    p_grid_kw: float | None = None
    p_import_kw: float = 0.0
    p_ev_kw: float = 0.0
    window_energy_kwh: float = 0.0
    window_elapsed_min: float = 0.0
    window_remaining_min: float = 15.0
    window_projection_kw: float = 0.0
    last_window_avg_kw: float | None = None
    last_window_exceeded: bool | None = None
    p_other_used_kw: float = 0.0
    i_house_a: tuple[float, float, float] = (0.0, 0.0, 0.0)
    i_phase_a: tuple[float, float, float] = (0.0, 0.0, 0.0)
    i_headroom_a: float = 0.0
    hard_threshold_count: int = 0
    # odločitev
    p_allow_kw: float | None = None
    p_ev_allow_kw: float | None = None
    candidate: str | None = None
    level: str | None = None
    tier: str = "idle"
    reason: str = "starting"
    decision_inputs: dict = field(default_factory=dict)
    # adapter
    last_car_command: str | None = None
    last_car_command_attrs: dict = field(default_factory=dict)


class SmartEvCoordinator(DataUpdateCoordinator[Snapshot]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=None)

    def push(self, snapshot: Snapshot) -> None:
        self.async_set_updated_data(snapshot)
