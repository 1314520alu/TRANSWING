#!/usr/bin/env bash
set -euo pipefail

ARDUPILOT_DIR="${ARDUPILOT_DIR:-$HOME/ardupilot}"
ARDUPILOT_VENV="${ARDUPILOT_VENV:-$HOME/venv-ardupilot}"
RUN_DIR="transwing_sitl"
LOG="/tmp/transwing_sitl_console.log"

cd "$ARDUPILOT_DIR/ArduPlane"

mkdir -p "$RUN_DIR/APM/scripts"
mkdir -p "$RUN_DIR/scripts"
cp /mnt/c/Users/alu/Desktop/TRANSWING/scripts/transwing_dynamic_mix.lua "$RUN_DIR/APM/scripts/transwing_dynamic_mix.lua"
cp /mnt/c/Users/alu/Desktop/TRANSWING/scripts/transwing_dynamic_mix.lua "$RUN_DIR/scripts/transwing_dynamic_mix.lua"
cp /mnt/c/Users/alu/Desktop/TRANSWING/transwing_sitl_startup.params "$RUN_DIR/transwing_sitl_startup.params"

rm -f "$LOG"

source "$ARDUPILOT_VENV/bin/activate"

../Tools/autotest/sim_vehicle.py \
  -v ArduPlane \
  -f quadplane-tilt \
  --use-dir "$RUN_DIR" \
  --add-param-file "$ARDUPILOT_DIR/ArduPlane/$RUN_DIR/transwing_sitl_startup.params" \
  --no-rebuild \
  --no-mavproxy \
  --no-extra-ports \
  --no-wsl2-network \
  -w >"$LOG" 2>&1 &

SIM_PID=$!

cleanup() {
  kill "$SIM_PID" 2>/dev/null || true
  pkill -f "build/sitl/bin/arduplane.*quadplane-tilt" 2>/dev/null || true
}
trap cleanup EXIT

"$ARDUPILOT_VENV/bin/python3" - <<'PY'
import time
from pymavlink import mavutil

master = None
last_error = None
for _ in range(80):
    try:
        master = mavutil.mavlink_connection("tcp:127.0.0.1:5760", autoreconnect=False, source_system=255)
        break
    except Exception as exc:
        last_error = exc
        time.sleep(0.5)

if master is None:
    raise SystemExit(f"connect failed: {last_error}")

master.wait_heartbeat(timeout=30)
print("HEARTBEAT OK")

messages = []
deadline = time.time() + 20
while time.time() < deadline:
    msg = master.recv_match(type="STATUSTEXT", blocking=True, timeout=1)
    if not msg:
        continue
    text = msg.text
    messages.append(text)
    print("STATUSTEXT", text)
    if "TW-DYNMIX" in text and "running" in text:
        break


def get_param(name):
    master.mav.param_request_read_send(master.target_system, master.target_component, name.encode("ascii"), -1)
    deadline = time.time() + 10
    while time.time() < deadline:
        msg = master.recv_match(type="PARAM_VALUE", blocking=True, timeout=1)
        if msg and msg.param_id.strip("\x00") == name:
            return msg.param_value
    raise RuntimeError(f"missing param {name}")


for name in [
    "SCR_ENABLE",
    "Q_ENABLE",
    "Q_TILT_ENABLE",
    "SERVO13_FUNCTION",
    "TW_ENABLE",
    "TW_LOG_ONLY",
    "TW_PWM_FW",
    "TW_PWM_Q",
    "TW_RATE_UP",
    "TW_RATE_DN",
    "TW_GUARD",
    "TW_SAFE_MIN",
    "TW_ACCEL_MIN",
    "TW_BLEND_MIN",
    "TW_ATT_ABORT",
    "TW_BLEND_AS",
    "TW_FW_AS",
]:
    print("PARAM", name, get_param(name))

if not any("TW-DYNMIX" in text for text in messages):
    print("NO_TW_STATUSTEXT_SEEN")


def set_param(name, value):
    master.mav.param_set_send(
        master.target_system,
        master.target_component,
        name.encode("ascii"),
        float(value),
        mavutil.mavlink.MAV_PARAM_TYPE_REAL32,
    )
    deadline = time.time() + 8
    while time.time() < deadline:
        msg = master.recv_match(type="PARAM_VALUE", blocking=True, timeout=1)
        if msg and msg.param_id.strip("\x00") == name:
            return msg.param_value
    raise RuntimeError(f"param set not confirmed: {name}")


print("SET_PARAM", "TW_THR", set_param("TW_THR", 0.5))
print("SET_PARAM", "TW_LOG_ONLY", set_param("TW_LOG_ONLY", 0))

master.mav.request_data_stream_send(
    master.target_system,
    master.target_component,
    mavutil.mavlink.MAV_DATA_STREAM_RAW_CONTROLLER,
    5,
    1,
)

deadline = time.time() + 10
servo_msg = None
while time.time() < deadline:
    msg = master.recv_match(type="SERVO_OUTPUT_RAW", blocking=True, timeout=1)
    if msg:
        servo_msg = msg
        values = [msg.servo13_raw, msg.servo14_raw, msg.servo15_raw, msg.servo16_raw]
        print("SERVO13_16", *values)
        if all(v > 1000 for v in values):
            break

if servo_msg is None:
    raise RuntimeError("missing SERVO_OUTPUT_RAW")
PY

echo
echo "--- SITL console tail ---"
tail -80 "$LOG"
