# gv_smart_home

Home Assistant integracija `smart_ev_charging`: polnjenje MG4 na Wallbox Pulsar Plus po
slovenskih omrežninskih blokih, z rezervo za porabnike hiše in varovalko po fazah.
Zasnova je v specu `docs/superpowers/specs/2026-09-14-smart-ev-charging-design.md`
(repo `homeassistant/claude`).

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=GorazdVeselic&repository=gv_smart_home&category=integration)

## Struktura

- `custom_components/smart_ev_charging/core/`: čista logika brez HA (koledar, bloki,
  stopnje, proračun okna, varovalka, glajenje, `decide()`, zaporedja ukazov, orkestrator).
- `custom_components/smart_ev_charging/*.py`: HA lepilo (engine, koordinator, adapter,
  config flow, senzorji, nastavitve).
- `sim/`: simulacija dneva brez HA in orodje za posnetek profila hiše s produkcije.
- `tests/`: pytest, brez HA.

## Zagon

```bash
.venv/bin/pytest
.venv/bin/python -m sim.run --date 2026-12-08 --pv winter --log
.venv/bin/python -m sim.fetch_profile --start 2026-09-14T22:00 --hours 24 --out sim/profiles/2026-09-15.csv
./sync-ha.sh   # rsync v dev docker instanco in restart
```
