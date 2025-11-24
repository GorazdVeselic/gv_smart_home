
TESTS: (coverage)
``` 
pytest --cov=custom_components/gv_smart_home --cov-report=term-missing -vv
```



- koliko daje elektranra (solar input)
states('sensor.solaredge_i1_ac_power')

- koliko gre v/iz omrežja (grid) 
- states('sensor.solaredge_i1_m1_ac_power')

## FAKE
```yaml

###############################################################################
# SIMULATED ENTITIES FOR SOLAREDGE, WALLBOX, MG4
###############################################################################

input_number:
  # SolarEdge simulated power
  simulated_solaredge_power:
    name: "Simulated SolarEdge AC Power"
    min: -13000
    max: 12000
    step: 100
    unit_of_measurement: "W"
    mode: slider
    initial: -2500

  # Wallbox simulated power
  simulated_wallbox_power:
    name: "Simulated Wallbox Power"
    min: 0
    max: 11000
    step: 100
    unit_of_measurement: "W"
    initial: 0

  # Wallbox set current
  simulated_wallbox_set_current:
    name: "Simulated Wallbox Set Current"
    min: 6
    max: 32
    step: 1
    unit_of_measurement: "A"
    initial: 6

  # MG4 real charging current
  simulated_mg4_current:
    name: "Simulated MG4 Real Charging Current"
    min: 0
    max: 32
    step: 1
    unit_of_measurement: "A"
    initial: 0

  # MG4 real reported charging limit
  simulated_mg4_current_limit_value:
    name: "Simulated MG4 Current Limit Value"
    min: 6
    max: 32
    step: 1
    unit_of_measurement: "A"
    initial: 6


input_boolean:
  # Wallbox on/off
  simulated_wallbox_charging_enable:
    name: "Simulated Wallbox: Charging Enable"
    icon: mdi:ev-station

  # Wallbox cable connected
  simulated_wallbox_cable_connected:
    name: "Simulated Wallbox Cable Connected"
    icon: mdi:power-plug
    initial: true

  # MG4 charging switch
  simulated_mg4_charging:
    name: "Simulated MG4 Charging"
    icon: mdi:car-electric
    initial: false

  # MG4 gun state
  simulated_mg4_gun_locked:
    name: "Simulated MG4 Gun Locked"
    icon: mdi:ev-plug-type1
    initial: true


input_select:
  # Wallbox status
  simulated_wallbox_status:
    name: "Simulated Wallbox Status"
    options:
      - idle
      - charging
      - error
      - complete
    initial: idle

  # MG4 current selector
  simulated_mg4_set_current:
    name: "Simulated MG4 Set Current"
    options:
      - "6"
      - "8"
      - "16"
      - "32"
    initial: "6"


###############################################################################
# TEMPLATE ENTITIES
###############################################################################

template:
  - sensor:
      - name: "solaredge_i1_m1_ac_power"
        unique_id: "simulated_solaredge_i1_m1_ac_power"
        state: "{{ states('input_number.simulated_solaredge_power') | float }}"
        unit_of_measurement: "W"

      - name: "wallbox_charging_power"
        unique_id: "simulated_wallbox_charging_power"
        state: "{{ states('input_number.simulated_wallbox_power') | float }}"
        unit_of_measurement: "W"

      - name: "wallbox_status"
        unique_id: "simulated_wallbox_status"
        state: "{{ states('input_select.simulated_wallbox_status') }}"

      - name: "mg_mg4_electric_charging_current_limit"
        unique_id: "simulated_mg4_current_limit"
        state: "{{ states('input_number.simulated_mg4_current_limit_value') | float }}"
        unit_of_measurement: "A"

  - binary_sensor:
      - name: "wallbox_cable_connected"
        unique_id: "simulated_wallbox_cable_connected"
        state: "{{ is_state('input_boolean.simulated_wallbox_cable_connected', 'on') }}"

      - name: "mg_mg4_electric_charging_gun_state"
        unique_id: "simulated_mg4_gun_state"
        state: "{{ is_state('input_boolean.simulated_mg4_gun_locked', 'on') }}"

  - switch:
      - name: "wallbox_charging_enable"
        unique_id: "simulated_wallbox_charging_enable"
        state: "{{ is_state('input_boolean.simulated_wallbox_charging_enable', 'on') }}"
        turn_on:
          service: input_boolean.turn_on
          target:
            entity_id: input_boolean.simulated_wallbox_charging_enable
        turn_off:
          service: input_boolean.turn_off
          target:
            entity_id: input_boolean.simulated_wallbox_charging_enable

      - name: "mg_mg4_electric_charging"
        unique_id: "simulated_mg4_charging_switch"
        state: "{{ is_state('input_boolean.simulated_mg4_charging', 'on') }}"
        turn_on:
          service: input_boolean.turn_on
          target:
            entity_id: input_boolean.simulated_mg4_charging
        turn_off:
          service: input_boolean.turn_off
          target:
            entity_id: input_boolean.simulated_mg4_charging

  - number:
      - name: "wallbox_max_charging_current"
        unique_id: "simulated_wallbox_max_current"
        state: "{{ states('input_number.simulated_wallbox_set_current') | float }}"
        min: 6
        max: 32
        step: 1
        unit_of_measurement: "A"
        set_value:
          service: input_number.set_value
          target:
            entity_id: input_number.simulated_wallbox_set_current
          data:
            value: "{{ value }}"

  - select:
      - name: "mg_mg4_electric_charging_current_limit"
        unique_id: "simulated_mg4_limit_select"
        state: "{{ states('input_select.simulated_mg4_set_current') }}"
        options:
          - "6"
          - "8"
          - "16"
          - "32"
        select_option:
          service: input_select.select_option
          target:
            entity_id: input_select.simulated_mg4_set_current
          data:
            option: "{{ option }}"

```



### CARD
```
type: custom:network-tariff-card
#entity: sensor.gv_smart_home_tariff
entity: sensor.gv_se_energy_info
name: Daily Tariff Blocks
showHours: true
offsetHours: false
outerRadius: 40
innerRadius: 32
colorMap:
  1: '#03045e'
  2: '#0077b6'
  3: '#00b4d8'
  4: '#90e0ef'
  5: '#caf0f8'
```
```
type: custom:gv-energy-tariff-card
entity: sensor.gv_se_energy_info
name: Daily Tariff Blocks
showHours: true
offsetHours: false
```
```
type: custom:gv-energy-tariff-card
entity: sensor.gv_se_energy_info
name: Daily Tariff Blocks
showHours: true
offsetHours: false
outerRadius: 40
innerRadius: 32
# Attribute on sensor.gv_se_energy_info, default: block_usage_percent
progress_attribute: block_usage_percent
colorMap:
  1: '#03045e'
  2: '#0077b6'
  3: '#00b4d8'
  4: '#90e0ef'
  5: '#caf0f8'
```

type: custom:gv-energy-tariff-bar-card
entity: sensor.gv_se_energy_info
name: Daily Tariff Blocks (Bar)
colorMap:
  1: '#03045e'
  2: '#0077b6'
  3: '#00b4d8'
  4: '#90e0ef'
  5: '#caf0f8'
