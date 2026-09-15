"""Sestavi ploščo za dev: polnjenje.yaml + pogled Avto (tvoja kartica z avtom iz
config/dashboards/car_card.json in koščki iz avto_koscki.yaml) + pogled Tablica.
Kliče ga sync-ha.sh. Kartica z avtom ni v gitu, ker je del produkcijske plošče.
"""

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "dashboards" / "polnjenje.yaml"
PIECES = ROOT / "dashboards" / "avto_koscki.yaml"
OUT = ROOT / "config" / "dashboards" / "polnjenje.yaml"
CAR = ROOT / "config" / "dashboards" / "car_card.json"


def main() -> None:
    d = yaml.safe_load(SRC.read_text())
    k = yaml.safe_load(PIECES.read_text())
    car = [json.loads(CAR.read_text())] if CAR.exists() else []
    entities = {"type": "entities", "entities": [{"entity": "switch.lsjwh4092rn039325_charging"}, {"entity": "select.lsjwh4092rn039325_charge_current_limit"}]}
    phone = {"title": "Avto (predogled)", "path": "avto", "icon": "mdi:car-electric", "type": "sections", "max_columns": 1,
             "sections": [{"type": "grid", "cards": car + k["tok_moci"] + k["telefon"] + [entities]}]}
    tablet = {"title": "Tablica (predogled)", "path": "tablica", "icon": "mdi:tablet", "type": "sections", "max_columns": 1,
              "sections": [{"type": "grid", "cards": k["tablica"]}]}
    d["views"] = [v for v in d["views"] if v.get("path") not in ("avto", "tablica")] + [phone, tablet]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False, width=200))
    print(f"plošča za dev: {OUT}")


if __name__ == "__main__":
    sys.exit(main())
