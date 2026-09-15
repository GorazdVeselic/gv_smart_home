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



# plošča za dev: polnjenje.yaml + predogled z avtom
./.venv/bin/python dashboards/build_dev_preview.py

docker restart gv-smarthome-dev

echo "container restarted"
