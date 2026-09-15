"""Konstante integracije. Vhodne entitete izbere uporabnik v config flowu (spec 4.1)."""

DOMAIN = "smart_ev_charging"

CONF_METER_POWER = "meter_power"
CONF_METER_POWER_A = "meter_power_a"
CONF_METER_POWER_B = "meter_power_b"
CONF_METER_POWER_C = "meter_power_c"
CONF_METER_VOLTAGE_A = "meter_voltage_a"
CONF_METER_VOLTAGE_B = "meter_voltage_b"
CONF_METER_VOLTAGE_C = "meter_voltage_c"
CONF_INVERT_METER = "invert_meter"
CONF_EV_CURRENT_L1 = "ev_current_l1"
CONF_EV_CURRENT_L2 = "ev_current_l2"
CONF_EV_CURRENT_L3 = "ev_current_l3"
CONF_EV_POWER = "ev_power"
CONF_WB_STATUS = "wb_status"
CONF_CABLE = "cable"
CONF_WB_ENABLE = "wb_enable"
CONF_WB_CURRENT = "wb_current"
CONF_CAR_LIMIT = "car_limit"
CONF_CAR_CHARGING = "car_charging"

CONF_BLOCK_POWER = ("block_1_power", "block_2_power", "block_3_power", "block_4_power", "block_5_power")
CONF_RESERVE = "reserve_power"
CONF_FUSE = "fuse_current"
CONF_FUSE_MARGIN = "fuse_margin"
CONF_KW_PER_AMP = "kw_per_amp"
CONF_MODE = "mode"

DEFAULT_ENTITIES = {
    CONF_METER_POWER: "sensor.solaredge_i1_m1_ac_power",
    CONF_METER_POWER_A: "sensor.solaredge_i1_m1_ac_power_a",
    CONF_METER_POWER_B: "sensor.solaredge_i1_m1_ac_power_b",
    CONF_METER_POWER_C: "sensor.solaredge_i1_m1_ac_power_c",
    CONF_METER_VOLTAGE_A: "sensor.solaredge_i1_m1_ac_voltage_an",
    CONF_METER_VOLTAGE_B: "sensor.solaredge_i1_m1_ac_voltage_bn",
    CONF_METER_VOLTAGE_C: "sensor.solaredge_i1_m1_ac_voltage_cn",
    CONF_EV_CURRENT_L1: "sensor.wallbox_charging_current_l1",
    CONF_EV_CURRENT_L2: "sensor.wallbox_charging_current_l2",
    CONF_EV_CURRENT_L3: "sensor.wallbox_charging_current_l3",
    CONF_EV_POWER: "sensor.wallbox_charging_power",
    CONF_WB_STATUS: "sensor.wallbox_status",
    CONF_CABLE: "binary_sensor.wallbox_cable_connected",
    CONF_WB_ENABLE: "switch.wallbox_charging_enable",
    CONF_WB_CURRENT: "number.wallbox_max_charging_current",
    CONF_CAR_LIMIT: "select.lsjwh4092rn039325_charge_current_limit",
    CONF_CAR_CHARGING: "switch.lsjwh4092rn039325_charging",
}

DEFAULT_BLOCK_POWER = (5.4, 7.1, 10.0, 10.0, 10.0)
DEFAULT_RESERVE = 2.0
DEFAULT_FUSE = 20.0
DEFAULT_FUSE_MARGIN = 3.0
DEFAULT_KW_PER_AMP = 0.69

MODES = ("off", "observe", "tariff")
DEFAULT_MODE = "observe"

TICK_SECONDS = (0, 30)
METER_STALE_SECONDS = 60
WB_BAD_STATUSES = ("Error", "Locked")

# dogodki za opozorila (spec 7a); avtomatizacija jih pošlje na telefon
EVENT_WINDOW_OVER_LIMIT = f"{DOMAIN}_window_over_limit"
EVENT_PHASE_OVER_MARGIN = f"{DOMAIN}_phase_over_margin"
EVENT_CAR_COMMAND_TIMEOUT = f"{DOMAIN}_car_command_timeout"
EVENT_METER_UNAVAILABLE = f"{DOMAIN}_meter_unavailable"
PHASE_OVER_MARGIN_SECONDS = 30
