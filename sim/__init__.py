"""Simulacija dneva brez HA (spec 8).

Uvaža `core` iz mape integracije na enak način kot testi.
"""

import sys
from pathlib import Path

INTEGRATION = Path(__file__).resolve().parents[1] / "custom_components" / "smart_ev_charging"
if str(INTEGRATION) not in sys.path:
    sys.path.insert(0, str(INTEGRATION))
