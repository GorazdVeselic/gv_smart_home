#!/usr/bin/env bash
set -euo pipefail

SRC="./custom_components/"
DST="./config/custom_components/"

echo "Sync custom_components -> config"

rsync -av --delete \
  --exclude "__pycache__/" \
  --exclude "*.pyc" \
  "$SRC" "$DST"

echo "sync done"



# plošča: produkcijski id-ji wallboxa -> simulirani
mkdir -p ./config/dashboards
sed -e 's/sensor\.wallbox_status/sensor.sim_wallbox_status/' \
    -e 's/sensor\.wallbox_charging_power/sensor.sim_wallbox_charging_power/' \
    -e 's/binary_sensor\.wallbox_cable_connected/binary_sensor.sim_cable_connected/' \
    ./dashboards/polnjenje.yaml > ./config/dashboards/polnjenje.yaml

docker restart gv-smarthome-dev

echo "container restarted"
