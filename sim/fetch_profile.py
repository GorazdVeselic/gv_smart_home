"""Potegne posnetek iz produkcijskega HA prek /api/history in zapiše profil hiše po fazah.

Izhod je CSV z vrstico na 10 s: čas, uvoz po fazah brez avta (kW, pozitivno poraba),
PV (kW), moč avta (kW). Profil hiše se vzame kot -P_x - P_ev/3, kjer je P_x moč faze
na števcu (pozitivno oddaja), plus PV/3, ker števec meri neto za PV.

Zagon: .venv/bin/python -m sim.fetch_profile --start 2026-09-14T22:00 --hours 24 --out sim/profiles/2026-09-15.csv
Token: ~/.secrets/ha_prod_token (dolgoživi token, samo branje).
"""

from __future__ import annotations

import argparse
import csv
import datetime
import json
import urllib.parse
import urllib.request
from pathlib import Path

HOST = "http://192.168.1.6:8123"
TOKEN_FILE = Path.home() / ".secrets" / "ha_prod_token"
STEP = datetime.timedelta(seconds=10)

ENTITIES = {
    "grid_a": "sensor.solaredge_i1_m1_ac_power_a",
    "grid_b": "sensor.solaredge_i1_m1_ac_power_b",
    "grid_c": "sensor.solaredge_i1_m1_ac_power_c",
    "pv": "sensor.solaredge_i1_ac_power",
    "ev": "sensor.wallbox_charging_power",
}


def fetch(entity: str, start: datetime.datetime, end: datetime.datetime) -> list[tuple[datetime.datetime, float]]:
    token = TOKEN_FILE.read_text().strip()
    url = (
        f"{HOST}/api/history/period/{urllib.parse.quote(start.isoformat())}"
        f"?filter_entity_id={entity}&end_time={urllib.parse.quote(end.isoformat())}&minimal_response&no_attributes"
    )
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.load(r)
    out = []
    for row in data[0] if data else []:
        try:
            out.append((datetime.datetime.fromisoformat(row["last_changed"]), float(row["state"])))
        except (ValueError, KeyError):
            continue
    return out


def resample(series: list[tuple[datetime.datetime, float]], start: datetime.datetime, n: int) -> list[float]:
    """Vrednost ob vsakem koraku: zadnja znana (prejšnja vrednost velja do naslednje)."""
    vals: list[float] = []
    i = 0
    cur = series[0][1] if series else 0.0
    for k in range(n):
        t = start + k * STEP
        while i < len(series) and series[i][0] <= t:
            cur = series[i][1]
            i += 1
        vals.append(cur)
    return vals


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help="lokalni čas, npr. 2026-09-14T22:00")
    ap.add_argument("--hours", type=float, default=24.0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    tz = datetime.datetime.now().astimezone().tzinfo
    start = datetime.datetime.fromisoformat(a.start).replace(tzinfo=tz)
    end = start + datetime.timedelta(hours=a.hours)
    n = int(a.hours * 3600 / STEP.total_seconds())

    cols = {name: resample(fetch(ent, start, end), start, n) for name, ent in ENTITIES.items()}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time", "house_a_kw", "house_b_kw", "house_c_kw", "pv_kw", "ev_kw"])
        for k in range(n):
            t = start + k * STEP
            pv = cols["pv"][k] / 1000
            ev = cols["ev"][k] / 1000
            house = [(-cols[g][k] / 1000) + pv / 3 - ev / 3 for g in ("grid_a", "grid_b", "grid_c")]
            w.writerow([t.isoformat(), *(f"{h:.3f}" for h in house), f"{pv:.3f}", f"{ev:.3f}"])
    print(f"{n} vrstic v {a.out}")


if __name__ == "__main__":
    main()
