"""Vstavi koščke iz avto_koscki.yaml v produkcijski plošči telefona in tablice
ter ustvari ploščo Polnjenje iz polnjenje.yaml. Vse prek websocketa, brez
pisanja v .storage in brez ponovnega zagona. Ponovljivo: stare koščke
(karte z entitetami ev_) najprej odstrani, zato je varno pognati večkrat.

  .venv/bin/python dashboards/deploy_prod.py           # samo pokaže, kaj bi naredil
  .venv/bin/python dashboards/deploy_prod.py --save    # zapiše
"""

import asyncio
import json
import re
import sys
from pathlib import Path

import websockets
import yaml

ROOT = Path(__file__).resolve().parents[1]
PIECES = ROOT / "dashboards" / "avto_koscki.yaml"
POLNJENJE = ROOT / "dashboards" / "polnjenje.yaml"
TABLICA = ROOT / "dashboards" / "tablica_polnjenje.yaml"
TOKEN = (Path.home() / ".secrets" / "ha_prod_token").read_text().strip()
WS = "ws://192.168.1.6:8123/api/websocket"

PHONE = "dashboard-mushroom"
TABLET = "dashboard-tablet"
EV = "ev-polnjenje"


def ours(card: dict) -> bool:
    return re.search(r"(sensor|select|switch|number)\.ev_", json.dumps(card)) is not None


class Ha:
    def __init__(self, ws):
        self.ws = ws
        self.n = 0

    async def call(self, **msg):
        self.n += 1
        await self.ws.send(json.dumps(dict(msg, id=self.n)))
        while True:
            r = json.loads(await self.ws.recv())
            if r.get("id") == self.n:
                if not r["success"]:
                    raise RuntimeError(r["error"])
                return r.get("result")


def patch_phone(cfg: dict, k: dict) -> None:
    view = next(v for v in cfg["views"] if v.get("path") == "builder")
    cards = view["sections"][0]["cards"]
    cards[:] = [c for c in cards if not ours(c)]
    i = next(i for i, c in enumerate(cards) if c.get("type") == "custom:button-card")
    cards[i + 1:i + 1] = k["tok_moci"] + k["telefon"]


def put_tablet_button(stack: dict, k: dict) -> None:
    """Gumb Polnjenje kot polje v kartici z avtom, nad gumbom Predgretje."""
    car = next(c for c in stack["cards"] if "mg4_preheat_button" in c.get("custom_fields", {}))
    car["custom_fields"]["ev_charging_button"] = k["tablica_gumb"]
    car["styles"]["custom_fields"]["ev_charging_button"] = k["tablica_gumb_polozaj"]


def patch_tablet(cfg: dict, k: dict, detail: dict) -> None:
    home = cfg["views"][0]

    def find_stack(c):
        if isinstance(c, dict):
            if c.get("type") == "vertical-stack" and any(
                "mg4_preheat_button" in x.get("custom_fields", {}) for x in c.get("cards", [])
            ):
                return c
            for key in ("cards", "card"):
                if key in c:
                    r = find_stack(c[key])
                    if r:
                        return r
        elif isinstance(c, list):
            for x in c:
                r = find_stack(x)
                if r:
                    return r
        return None

    stack = find_stack(home["cards"])
    if stack is None:
        raise SystemExit("tablica: vertical-stack s kartico avta ni najden")
    stack["cards"] = [c for c in stack["cards"] if not ours(c)]
    put_tablet_button(stack, k)
    cfg["views"] = [v for v in cfg["views"] if v.get("path") != detail["path"]] + [detail]


async def main(save: bool) -> None:
    k = yaml.safe_load(PIECES.read_text())
    polnjenje = yaml.safe_load(POLNJENJE.read_text())
    detail = yaml.safe_load(TABLICA.read_text())

    async with websockets.connect(WS, max_size=None) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": TOKEN}))
        assert json.loads(await ws.recv())["type"] == "auth_ok"
        ha = Ha(ws)

        phone = await ha.call(type="lovelace/config", url_path=PHONE)
        patch_phone(phone, k)
        n = len(phone["views"][1]["sections"][0]["cards"])
        print(f"telefon: pogled builder ima {n} kart, od tega {sum(ours(c) for c in phone['views'][1]['sections'][0]['cards'])} naših")

        tablet = await ha.call(type="lovelace/config", url_path=TABLET)
        patch_tablet(tablet, k, detail)
        print(f"tablica: pogledi {[v.get('path') for v in tablet['views']]}")

        dashboards = await ha.call(type="lovelace/dashboards/list")
        exists = any(d["url_path"] == EV for d in dashboards)
        print(f"plošča {EV}: {'obstaja, prepišem' if exists else 'ustvarim'}")

        if not save:
            print("suhi tek, nič zapisano (--save za zapis)")
            return
        await ha.call(type="lovelace/config/save", url_path=PHONE, config=phone)
        await ha.call(type="lovelace/config/save", url_path=TABLET, config=tablet)
        if not exists:
            await ha.call(type="lovelace/dashboards/create", url_path=EV, title=polnjenje["title"],
                          icon="mdi:ev-station", show_in_sidebar=True, require_admin=False)
        await ha.call(type="lovelace/config/save", url_path=EV, config=polnjenje)
        print("zapisano")


if __name__ == "__main__":
    asyncio.run(main("--save" in sys.argv))
