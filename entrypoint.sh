#!/bin/sh
set -e

mkdir -p /output/data

# Preserve cached data files across container restarts/updates
if [ -f /output/data/specs.json ]; then
  cp /output/data/specs.json /tmp/specs.json.bak
fi
if [ -f /output/data/games.json ]; then
  cp /output/data/games.json /tmp/games.json.bak
fi

cp -r /app/dist/* /output/

if [ -f /tmp/specs.json.bak ]; then
  mv /tmp/specs.json.bak /output/data/specs.json
fi
if [ -f /tmp/games.json.bak ]; then
  mv /tmp/games.json.bak /output/data/games.json
fi

NETFETCH_INTERVAL="${NETFETCH_INTERVAL:-60}"
STEAM_INTERVAL="${STEAM_INTERVAL:-3600}"

trap 'kill 0' TERM INT

# Steam games polling loop
(
  while true; do
    if python3 /app/scripts/steam-data-fetcher.py; then
      cp /app/public/data/games.json /output/data/games.json.tmp
      mv /output/data/games.json.tmp /output/data/games.json
    else
      echo "[entrypoint] steam-data-fetcher failed, keeping previous games.json" >&2
    fi
    sleep "$STEAM_INTERVAL"
  done
) &

# Netfetch specs polling loop
(
  while true; do
    if ! NETFETCH_OUTPUT_PATH=/output/data/specs.json python3 /app/scripts/netfetch-fetcher.py; then
      echo "[entrypoint] netfetch-fetcher failed, keeping previous specs.json" >&2
    fi
    sleep "$NETFETCH_INTERVAL"
  done
) &

wait
