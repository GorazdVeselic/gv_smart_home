"""Testi jedra tečejo brez Home Assistanta.

`core` se uvozi kot samostojen paket iz mape integracije, ker bi uvoz prek
`custom_components.smart_ev_charging` potegnil `__init__.py` in z njim HA.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "smart_ev_charging"
for p in (INTEGRATION, ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
