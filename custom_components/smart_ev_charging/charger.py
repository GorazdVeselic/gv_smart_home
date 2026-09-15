"""Charger adapter za HA (spec 6.5): AdapterCore izvaja s service klici.

Med zaporedjem teče izvajalec vsako sekundo, bere potrditve iz stanj entitet
in pošlje naslednji korak. Ukazi:
- tok wallboxa: number.set_value
- wallbox enable: switch.turn_on / turn_off
- meja avta: select.select_option (oblak)
- zagon avta: switch.turn_on (oblak)
"""

from __future__ import annotations

import datetime
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt as dt_util

from .const import CONF_CAR_CHARGING, CONF_CAR_LIMIT, CONF_EV_POWER, CONF_WB_CURRENT, CONF_WB_ENABLE, CONF_WB_STATUS
from .core.levels import Level
from .core.models import Decision
from .core.sequences import CMD_CAR_LIMIT, CMD_CAR_START, CMD_WB_CURRENT, CMD_WB_ENABLE, AdapterCore, Observation, Step

_LOGGER = logging.getLogger(__name__)
RUN_INTERVAL_S = 1.0


class Charger:
    def __init__(self, hass: HomeAssistant, cfg_values: dict, levels: list[Level]) -> None:
        self.hass = hass
        self.cfg = cfg_values
        self.core = AdapterCore(levels)
        self._timer_unsub = None

    # ------------------------------------------------------------------
    def _float(self, key: str) -> float | None:
        st = self.hass.states.get(self.cfg[key])
        if st is None:
            return None
        try:
            return float(st.state)
        except ValueError:
            return None

    def observation(self) -> Observation:
        st = self.hass.states.get(self.cfg[CONF_WB_STATUS])
        return Observation(
            wb_current=int(self._float(CONF_WB_CURRENT) or 0),
            wb_status=st.state if st else "unavailable",
            p_ev_kw=(self._float(CONF_EV_POWER) or 0.0) / 1000.0,
        )

    async def _execute(self, steps: list[Step]) -> None:
        for s in steps:
            _LOGGER.info("ukaz %s=%s", s.cmd, s.value)
            if s.cmd == CMD_WB_CURRENT:
                await self.hass.services.async_call(
                    "number", "set_value", {"entity_id": self.cfg[CONF_WB_CURRENT], "value": s.value}, blocking=True
                )
            elif s.cmd == CMD_WB_ENABLE:
                await self.hass.services.async_call(
                    "switch", "turn_on" if s.value else "turn_off", {"entity_id": self.cfg[CONF_WB_ENABLE]}, blocking=True
                )
            elif s.cmd == CMD_CAR_LIMIT:
                await self.hass.services.async_call(
                    "select", "select_option", {"entity_id": self.cfg[CONF_CAR_LIMIT], "option": s.value}, blocking=True
                )
            elif s.cmd == CMD_CAR_START:
                await self.hass.services.async_call(
                    "switch", "turn_on", {"entity_id": self.cfg[CONF_CAR_CHARGING]}, blocking=True
                )

    # ------------------------------------------------------------------
    async def hard_threshold(self, now: datetime.datetime) -> None:
        await self._execute(self.core.hard_threshold(now))
        self._schedule()

    async def apply(self, d: Decision, now: datetime.datetime) -> None:
        await self._execute(self.core.apply(d, now, self.observation()))
        self._schedule()

    async def advance(self, now: datetime.datetime) -> None:
        await self._execute(self.core.advance(now, self.observation()))
        self._schedule()

    def _schedule(self) -> None:
        if self.core.busy and self._timer_unsub is None:
            self._timer_unsub = async_call_later(self.hass, RUN_INTERVAL_S, self._on_timer)

    @callback
    def _on_timer(self, _now) -> None:
        self._timer_unsub = None
        self.hass.async_create_task(self.advance(dt_util.now()))

    def stop(self) -> None:
        if self._timer_unsub is not None:
            self._timer_unsub()
            self._timer_unsub = None
