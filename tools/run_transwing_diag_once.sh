#!/usr/bin/env bash
set -euo pipefail

ARDUPILOT_DIR="${ARDUPILOT_DIR:-$HOME/ardupilot}"
INSTANCE="${INSTANCE:-8}"
BASE_PORT=$((5760 + INSTANCE * 10))
LOG_FILE="/tmp/transwing_diag_sitl_${INSTANCE}.log"
PID_FILE="/tmp/transwing_diag_sitl_${INSTANCE}.pid"

source "$HOME/venv-ardupilot/bin/activate" 2>/dev/null || true
cd "$ARDUPILOT_DIR"

pkill -f "arduplane.*quadplane-transwing.*-I ${INSTANCE}" 2>/dev/null || true
rm -f "$LOG_FILE" "$PID_FILE"

./build/sitl/bin/arduplane \
    -M quadplane-transwing \
    -I "$INSTANCE" \
    -s 1 \
    -O 35,149,584,0 \
    --defaults Tools/autotest/default_params/quadplane-transwing.parm \
    >"$LOG_FILE" 2>&1 &

pid=$!
echo "$pid" > "$PID_FILE"
cleanup() {
    kill "$pid" 2>/dev/null || true
}
trap cleanup EXIT

sleep 2
python3 /mnt/c/Users/alu/Desktop/TRANSWING/tools/diagnose_mav_outputs.py "tcp:127.0.0.1:${BASE_PORT}" "$@"
tail -40 "$LOG_FILE"
