"""Povezuje dogodke HA s core.Controller (spec 5).

Viri dogodkov:
1. sprememba stanja števca -> Controller.on_meter (trdi prag)
2. sprememba wallboxa (moč, status, kabel) -> osvežitev posnetka, ob priklopu kabla tick
3. in 4. tick ob :00 in :30 vsake minute -> Controller.tick; ob polni uri je to hkrati
   nov blok, ker Controller blok bere iz ure

Ukazov ta korak še ne pošilja (način observe); adapter pride v charger.py.
"""

from __future__ import annotations

import dataclasses
import datetime
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_change
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_BLOCK_POWER,
    CONF_CABLE,
    CONF_CAR_LIMIT,
    CONF_EV_CURRENT_L1,
    CONF_EV_CURRENT_L2,
    CONF_EV_CURRENT_L3,
    CONF_EV_POWER,
    CONF_FUSE,
    CONF_FUSE_MARGIN,
    CONF_INVERT_METER,
    CONF_KW_PER_AMP,
    CONF_METER_POWER,
    CONF_METER_POWER_A,
    CONF_METER_POWER_B,
    CONF_METER_POWER_C,
    CONF_METER_VOLTAGE_A,
    CONF_METER_VOLTAGE_B,
    CONF_METER_VOLTAGE_C,
    CONF_MODE,
    CONF_RESERVE,
    CONF_WB_CURRENT,
    CONF_WB_STATUS,
    DEFAULT_BLOCK_POWER,
    DEFAULT_FUSE,
    DEFAULT_FUSE_MARGIN,
    DEFAULT_KW_PER_AMP,
    DEFAULT_MODE,
    DEFAULT_RESERVE,
    METER_STALE_SECONDS,
    TICK_SECONDS,
    WB_BAD_STATUSES,
)
from homeassistant.helpers.storage import Store

from .charger import Charger
from .coordinator import SmartEvCoordinator, Snapshot
from .core.calendar import get_holiday_name, is_holiday, is_weekend
from .core.controller import Config, Controller
from .core.fuse import PhaseCurrents
from .core.levels import lowest_charging_level
from .core.models import MODE_TARIFF, ChargerState, Decision, RegulatorState, TIER_LOW
from .core.tariff import get_prev_next_block_info, is_high_season

STORE_VERSION = 1

_LOGGER = logging.getLogger(__name__)


class Engine:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, coordinator: SmartEvCoordinator) -> None:
        self.hass = hass
        self.entry = entry
        self.coordinator = coordinator
        self.cfg_values = {**entry.data, **entry.options}
        self.mode: str = self.cfg_values.get(CONF_MODE, DEFAULT_MODE)
        now = dt_util.now()
        self.controller = Controller(self._config(), now)
        self.charger = Charger(hass, self.cfg_values, self.controller.levels)
        self._store: Store = Store(hass, STORE_VERSION, f"{DOMAIN}.{entry.entry_id}.state")
        self._last_meter: datetime.datetime | None = None
        self._started = now
        self._last_cable: bool | None = None
        self._hard_count = 0
        self._unsubs: list = []

    # ------------------------------------------------------------------
    # življenjski cikel
    # ------------------------------------------------------------------
    def _config(self) -> Config:
        v = self.cfg_values
        return Config(
            block_power_kw={i + 1: float(v.get(key, DEFAULT_BLOCK_POWER[i])) for i, key in enumerate(CONF_BLOCK_POWER)},
            reserve_kw=float(v.get(CONF_RESERVE, DEFAULT_RESERVE)),
            fuse_a=float(v.get(CONF_FUSE, DEFAULT_FUSE)),
            fuse_margin_a=float(v.get(CONF_FUSE_MARGIN, DEFAULT_FUSE_MARGIN)),
            kw_per_amp=float(v.get(CONF_KW_PER_AMP, DEFAULT_KW_PER_AMP)),
        )

    def update_config(self, **changes: float) -> None:
        """Nastavitve iz UI (number entitete) spremenijo Config, zgodovina ostane."""
        self.cfg_values.update(changes)
        self.controller.cfg = self._config()
        if CONF_KW_PER_AMP in changes:
            self.controller.levels = Controller(self._config(), dt_util.now()).levels

    def set_mode(self, mode: str) -> None:
        """Preklop načina (spec 6.6): v tariff se raven ob naslednjem ticku ugotovi iz P_ev.

        Lastna pavza se ohrani, sicer bi vrnitev iz pavze izgubila zagon avta.
        """
        if mode == self.mode:
            return
        self.mode = mode
        _LOGGER.info("način %s", mode)
        if mode == MODE_TARIFF and self.controller.state.level != "off":
            self.controller.state = RegulatorState()
            self.charger.core.level = None
        if self._unsubs:
            self._tick(dt_util.now())

    async def _async_restore(self) -> None:
        data = await self._store.async_load()
        if not data:
            return
        try:
            st = RegulatorState(
                level=data.get("level"),
                tier_since=dt_util.parse_datetime(data["tier_since"]) if data.get("tier_since") else None,
                level_since=dt_util.parse_datetime(data["level_since"]) if data.get("level_since") else None,
            )
        except (KeyError, TypeError, ValueError):
            return
        self.controller.state = st
        self.charger.core.level = st.level
        _LOGGER.info("obnovljeno stanje: %s", st.level)

    def _save_state(self) -> None:
        st = self.controller.state
        self._store.async_delay_save(
            lambda: {
                "level": st.level,
                "tier_since": st.tier_since.isoformat() if st.tier_since else None,
                "level_since": st.level_since.isoformat() if st.level_since else None,
            },
            5,
        )

    async def async_start(self) -> None:
        await self._async_restore()
        meter_ids = [self.cfg_values[k] for k in (CONF_METER_POWER, CONF_METER_POWER_A, CONF_METER_POWER_B, CONF_METER_POWER_C)]
        charger_ids = [self.cfg_values[k] for k in (CONF_EV_POWER, CONF_WB_STATUS, CONF_CABLE, CONF_WB_CURRENT, CONF_CAR_LIMIT)]
        self._unsubs.append(async_track_state_change_event(self.hass, [meter_ids[0]], self._on_meter_event))
        self._unsubs.append(async_track_state_change_event(self.hass, charger_ids, self._on_charger_event))
        self._unsubs.append(async_track_time_change(self.hass, self._on_tick, second=list(TICK_SECONDS)))
        self._on_meter(dt_util.now())
        self._tick(dt_util.now())

    def stop(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        self.charger.stop()

    # ------------------------------------------------------------------
    # branje entitet
    # ------------------------------------------------------------------
    def _state(self, key: str) -> State | None:
        st = self.hass.states.get(self.cfg_values[key])
        if st is None or st.state in ("unknown", "unavailable", ""):
            return None
        return st

    def _float(self, key: str) -> float | None:
        st = self._state(key)
        if st is None:
            return None
        try:
            return float(st.state)
        except ValueError:
            return None

    def _bool(self, key: str) -> bool | None:
        st = self._state(key)
        if st is None:
            return None
        return st.state.lower() in ("on", "true", "1", "connected")

    def _meter_ok(self, now: datetime.datetime) -> bool:
        """Zadnji dober vzorec pred manj kot 60 s (spec 6.6: nedosegljiv ali zamrznjen)."""
        ref = self._last_meter or self._started
        return (now - ref).total_seconds() <= METER_STALE_SECONDS

    def _wallbox_ok(self) -> bool:
        st = self._state(CONF_WB_STATUS)
        return st is not None and st.state not in WB_BAD_STATUSES and self._float(CONF_EV_POWER) is not None

    def _p_grid_kw(self) -> float | None:
        p = self._float(CONF_METER_POWER)
        if p is None:
            return None
        return (-p if self.cfg_values.get(CONF_INVERT_METER) else p) / 1000.0

    def _phases(self) -> PhaseCurrents:
        sign = -1.0 if self.cfg_values.get(CONF_INVERT_METER) else 1.0
        power = tuple(sign * (self._float(k) or 0.0) for k in (CONF_METER_POWER_A, CONF_METER_POWER_B, CONF_METER_POWER_C))
        volt = tuple(self._float(k) for k in (CONF_METER_VOLTAGE_A, CONF_METER_VOLTAGE_B, CONF_METER_VOLTAGE_C))
        return PhaseCurrents.from_power_w(power, volt)  # type: ignore[arg-type]

    def _p_ev_kw(self) -> float:
        return (self._float(CONF_EV_POWER) or 0.0) / 1000.0

    def _i_ev_a(self) -> float:
        vals = [self._float(k) for k in (CONF_EV_CURRENT_L1, CONF_EV_CURRENT_L2, CONF_EV_CURRENT_L3)]
        known = [v for v in vals if v is not None]
        return sum(known) / len(known) if known else 0.0

    def charger_state(self) -> ChargerState:
        st = self._state(CONF_WB_STATUS)
        limit = self._state(CONF_CAR_LIMIT)
        return ChargerState(
            cable_connected=bool(self._bool(CONF_CABLE)),
            status=st.state if st else "unavailable",
            p_ev_kw=self._p_ev_kw(),
            wb_current=int(self._float(CONF_WB_CURRENT) or 6),
            car_limit=limit.state if limit else None,
        )

    # ------------------------------------------------------------------
    # dogodki
    # ------------------------------------------------------------------
    @callback
    def _on_meter_event(self, event: Event) -> None:
        self._on_meter(dt_util.now())

    def _on_meter(self, now: datetime.datetime) -> None:
        p_grid = self._p_grid_kw()
        st = self._state(CONF_METER_POWER)
        if p_grid is None or st is None or (now - st.last_updated).total_seconds() > METER_STALE_SECONDS:
            self._push(now)
            return
        self._last_meter = now
        hard = self.controller.on_meter(now, p_grid, self._phases(), self._p_ev_kw(), self._i_ev_a())
        if hard:
            self._hard_count += 1
            _LOGGER.debug("trdi prag ob %s, uvoz %.2f kW", now, max(-p_grid, 0.0))
            if self.mode == MODE_TARIFF and self._wallbox_ok():
                self.hass.async_create_task(self.charger.hard_threshold(now))
        self._push(now)

    @callback
    def _on_charger_event(self, event: Event) -> None:
        now = dt_util.now()
        cable = self._bool(CONF_CABLE)
        if cable and self._last_cable is False:
            self._tick(now)  # ob priklopu kabla začetna odločitev
        else:
            self._push(now)
        self._last_cable = cable

    @callback
    def _on_tick(self, now: datetime.datetime) -> None:
        self._tick(dt_util.as_local(now))

    def _tick(self, now: datetime.datetime) -> None:
        before = self.controller.state.level
        d = self.controller.tick(now, self.charger_state(), self.mode)
        d = self._apply_failures(d, now)
        if d.state.level != before:
            self._save_state()
        if self.mode == MODE_TARIFF and self._wallbox_ok():
            if self.charger.core.level is None and d.previous_level is not None:
                self.charger.core.level = d.previous_level
            self.hass.async_create_task(self.charger.apply(d, now))
        self._push(now)

    def _apply_failures(self, d: Decision, now: datetime.datetime) -> Decision:
        """Spec 6.5: števec nedosegljiv ali zamrznjen več kot 60 s -> car_6A."""
        if d.level in (None, "off") or self._meter_ok(now):
            return d
        floor = lowest_charging_level(self.controller.levels)
        st = dataclasses.replace(d.state, level=floor.name)
        self.controller.state = st
        self.controller.last_decision = d = dataclasses.replace(d, level=floor.name, tier=TIER_LOW, reason="meter_unavailable", state=st)
        return d

    # ------------------------------------------------------------------
    # posnetek
    # ------------------------------------------------------------------
    def _push(self, now: datetime.datetime) -> None:
        ctl = self.controller
        tariff = ctl.tariff_at(now)
        info = get_prev_next_block_info(now)
        date = now.date()
        d = ctl.last_decision
        p_grid = self._p_grid_kw()
        p_ev = self._p_ev_kw()
        snap = Snapshot(
            now=now,
            mode=self.mode,
            block=tariff.block,
            agreed_kw=tariff.agreed_kw,
            reserve_kw=tariff.reserve_kw,
            target_kw=tariff.target_kw,
            tariff_attrs={
                "next_block": info["next_block"],
                "minutes_to_next": info["minutes_to_next"],
                "high_season": is_high_season(date),
                "weekend": is_weekend(date),
                "holiday": is_holiday(date),
                "holiday_name": get_holiday_name(date),
            },
            meter_ok=self._meter_ok(now),
            wallbox_ok=self._wallbox_ok(),
            p_grid_kw=p_grid,
            p_import_kw=max(-p_grid, 0.0) if p_grid is not None else 0.0,
            p_ev_kw=p_ev,
            window_energy_kwh=ctl.window.energy_kwmin / 60.0,
            window_elapsed_min=ctl.window.elapsed(now),
            window_remaining_min=ctl.window.remaining(now),
            window_projection_kw=ctl.window.projected_average_kw(now, max(-p_grid, 0.0) if p_grid is not None else 0.0),
            last_window_avg_kw=ctl.window.last_window.average_kw if ctl.window.last_window else None,
            last_window_exceeded=ctl.window.last_window.exceeded if ctl.window.last_window else None,
            p_other_used_kw=ctl.p_other_used_kw,
            i_house_a=ctl.i_house_used_a,
            i_headroom_a=ctl.i_headroom_a,
            hard_threshold_count=self._hard_count,
            p_allow_kw=d.p_allow_kw if d else None,
            p_ev_allow_kw=d.p_ev_allow_kw if d else None,
            candidate=d.candidate if d else None,
            level=d.level if d else None,
            tier=d.tier if d else "idle",
            reason=d.reason if d else "starting",
            decision_inputs=dataclasses.asdict(ctl.state) if d else {},
            last_car_command=f"{lc[0]}={lc[1]}: {lc[2]}" if (lc := self.charger.core.last_command) else None,
            last_car_command_attrs={
                "time": self.charger.core.last_command_time,
                "adapter_level": self.charger.core.level,
                "busy": self.charger.core.busy,
                "timeouts": self.charger.core.timeouts,
                "rate_limited": self.charger.core.rate_limited,
            },
        )
        self.coordinator.push(snap)
