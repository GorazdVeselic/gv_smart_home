DOMAIN = "gv_smart_home"

# -------------------------------------------------------------
# House Consumption Sampling Configuration
# -------------------------------------------------------------
# How often to take a sample (seconds)
HC_SAMPLE_INTERVAL_SECONDS = 10
# How long history we keep (minutes)
HC_WINDOW_MINUTES = 15

# Charging controller ow often control loop runs
CC_INTERVAL_MINUTES = 1
RAMP_DOWN_MINUTES_BEFORE=10
# Block transition rules
RAMP_UP_MAX_STEP_W = 2300  # ≈ 2 A per minute ramp-up

COORDINATOR_INTERVAL_MINUTES = 3

CONF_BLOCK_1 = "block_1_power"
CONF_BLOCK_2 = "block_2_power"
CONF_BLOCK_3 = "block_3_power"
CONF_BLOCK_4 = "block_4_power"
CONF_BLOCK_5 = "block_5_power"

CONF_GRID_POWER_ENTITY = "house_consumption_entity"

CONF_WB_POWER = "wallbox_charging_power"
CONF_WB_SET_CURRENT = "wallbox_set_current"
CONF_WB_CABLE = "wallbox_cable_connected"
CONF_WB_STATUS = "wallbox_status"

CONF_MG_ACTIVE = "mg4_charging_active"
CONF_MG_SET_CURRENT = "mg4_set_current"
CONF_MG_GUN_STATE = "mg4_gun_state"
