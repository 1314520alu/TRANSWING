#!/usr/bin/env bash
set -euo pipefail

ARDUPILOT_DIR="${ARDUPILOT_DIR:-$HOME/ardupilot}"
ARDUPILOT_VENV="${ARDUPILOT_VENV:-$HOME/venv-ardupilot}"
RUN_DIR="transwing_sitl"

cd "$ARDUPILOT_DIR/ArduPlane"

mkdir -p "$RUN_DIR/APM/scripts"
mkdir -p "$RUN_DIR/scripts"
cp /mnt/c/Users/alu/Desktop/TRANSWING/scripts/transwing_dynamic_mix.lua "$RUN_DIR/APM/scripts/transwing_dynamic_mix.lua"
cp /mnt/c/Users/alu/Desktop/TRANSWING/scripts/transwing_dynamic_mix.lua "$RUN_DIR/scripts/transwing_dynamic_mix.lua"
cp /mnt/c/Users/alu/Desktop/TRANSWING/transwing_sitl_mp.params "$RUN_DIR/transwing_sitl_mp.params"

source "$ARDUPILOT_VENV/bin/activate"

WINDOWS_HOST="${WINDOWS_HOST:-$(awk '/nameserver/ {print $2; exit}' /etc/resolv.conf)}"
MP_PORT="${MP_PORT:-14550}"

echo "Starting Transwing ArduPlane quadplane-tilt SITL"
echo "Mission Planner UDP target: ${WINDOWS_HOST}:${MP_PORT}"
echo
echo "In Mission Planner, choose UDP and port ${MP_PORT}."
echo "Keep this terminal open while using the simulator."
echo

../Tools/autotest/sim_vehicle.py \
  -v ArduPlane \
  -f quadplane-tilt \
  --use-dir "$RUN_DIR" \
  --add-param-file "$ARDUPILOT_DIR/ArduPlane/$RUN_DIR/transwing_sitl_mp.params" \
  --no-rebuild \
  --out "udp:${WINDOWS_HOST}:${MP_PORT}"
