#!/bin/sh
set -e

mkdir -p /output
cp -r /app/dist/* /output/

while true; do
  python3 /app/scripts/steam-data-fetcher.py
  cp /app/public/games.json /output/games.json
  sleep 3600
done