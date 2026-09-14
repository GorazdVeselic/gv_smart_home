#!/usr/bin/env bash
set -euo pipefail

SRC="./custom_components/"
DST="./config/custom_components/"

echo "▶ Syncing custom_components → Home Assistant config"

rsync -av --delete \
  --exclude "__pycache__/" \
  --exclude "*.pyc" \
  "$SRC" "$DST"

echo "✅ Sync complete"



docker restart gv-smarthome-dev

echo "✅ container restarted"
