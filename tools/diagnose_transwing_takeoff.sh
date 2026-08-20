#!/usr/bin/env bash
set -euo pipefail

ARDUPILOT_DIR="${ARDUPILOT_DIR:-$HOME/ardupilot}"
ARDUPILOT_VENV="${ARDUPILOT_VENV:-$HOME/venv-ardupilot}"
MODE="${1:-current}"
RUN_DIR="transwing_takeoff_diag_${MODE}"
LOG="/tmp/transwing_takeoff_diag_${MODE}.log"

cd "$ARDUPILOT_DIR/ArduPlane"
mkdir -p "$RUN_DIR/scripts" "$RUN_DIR/APM/scripts"
cp /mnt/c/Users/alu/Desktop/TRANSWING/scripts/transwing_dynamic_mix.lua "$RUN_DIR/scripts/transwing_dynamic_mix.lua"
cp /mnt/c/Users/alu/Desktop/TRANSWING/scripts/transwing_dynamic_mix.lua "$RUN_DIR/APM/scripts/transwing_dynamic_mix.lua"

PARAM_FILE="$RUN_DIR/params.parm"
if [[ "$MODE" == "default-motors" ]]; then
  cat > "$PARAM_FILE" <<'PARM'
SCR_ENABLE,1
Q_ENABLE,1
Q_FRAME_CLASS,1
Q_FRAME_TYPE,1
Q_TILT_ENABLE,1
Q_TILT_MASK,15
Q_TILT_TYPE,0
Q_TILT_MAX,45
Q_TILT_RATE_UP,4.5
Q_TILT_RATE_DN,4.5
SERVO1_FUNCTION,4
SERVO2_FUNCTION,19
SERVO3_FUNCTION,21
SERVO4_FUNCTION,70
SERVO5_FUNCTION,33
SERVO6_FUNCTION,34
SERVO7_FUNCTION,35
SERVO8_FUNCTION,36
SERVO13_FUNCTION,94
SERVO14_FUNCTION,95
SERVO15_FUNCTION,96
SERVO16_FUNCTION,97
PARM
else
  cp /mnt/c/Users/alu/Desktop/TRANSWING/transwing_sitl_startup.params "$PARAM_FILE"
fi

source "$ARDUPILOT_VENV/bin/activate"
rm -f "$LOG"

../Tools/autotest/sim_vehicle.py \
  -v ArduPlane \
  -f quadplane-tilt \
  --use-dir "$RUN_DIR" \
  --add-param-file "$ARDUPILOT_DIR/ArduPlane/$PARAM_FILE" \
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

"$ARDUPILOT_VENV/bin/python3" - "$MODE" <<'PY'
import sys
import time
from pymavlink import mavutil

mode_name = sys.argv[1]

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
print("CASE", mode_name)
print("HEARTBEAT OK")

def request_stream(stream_id, rate):
    master.mav.request_data_stream_send(master.target_system, master.target_component, stream_id, rate, 1)

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

def get_param(name):
    master.mav.param_request_read_send(master.target_system, master.target_component, name.encode("ascii"), -1)
    deadline = time.time() + 8
    while time.time() < deadline:
        msg = master.recv_match(type="PARAM_VALUE", blocking=True, timeout=1)
        if msg and msg.param_id.strip("\x00") == name:
            return msg.param_value
    raise RuntimeError(f"missing param {name}")

deadline = time.time() + 15
while time.time() < deadline:
    msg = master.recv_match(type="STATUSTEXT", blocking=True, timeout=1)
    if msg:
        print("STATUSTEXT", msg.text)
        if "Ready" in msg.text or "TW-DYNMIX" in msg.text:
            break

mapping = master.mode_mapping()
mode_id = mapping.get("QHOVER") or mapping.get("QSTABILIZE")
if mode_id is None:
    raise RuntimeError("QHOVER/QSTABILIZE mode not found")
master.set_mode(mode_id)
time.sleep(1)

master.arducopter_arm()
time.sleep(3)
print("ARMED_STATE", master.motors_armed())

request_stream(mavutil.mavlink.MAV_DATA_STREAM_RAW_CONTROLLER, 10)
request_stream(mavutil.mavlink.MAV_DATA_STREAM_POSITION, 10)

def rc_override(throttle):
    values = [1500, 1500, throttle, 1500, 1500, 1500, 1500, 1500]
    master.mav.rc_channels_override_send(master.target_system, master.target_component, *values)

start_alt = None
last_alt = None
last_servo = None
for i in range(80):
    rc_override(1800)
    deadline = time.time() + 0.2
    while time.time() < deadline:
        msg = master.recv_match(blocking=True, timeout=0.05)
        if not msg:
            continue
        mtype = msg.get_type()
        if mtype == "GLOBAL_POSITION_INT":
            alt = msg.relative_alt / 1000.0
            if start_alt is None:
                start_alt = alt
            last_alt = alt
        elif mtype == "SERVO_OUTPUT_RAW":
            last_servo = [msg.servo1_raw, msg.servo2_raw, msg.servo3_raw, msg.servo4_raw, msg.servo5_raw, msg.servo6_raw, msg.servo7_raw, msg.servo8_raw]
    if i in (10, 30, 60, 79):
        print("SAMPLE", i, "relalt", last_alt, "servo1_8", last_servo)

if start_alt is None or last_alt is None:
    print("ALT_RESULT missing")
else:
    print("ALT_RESULT", "start", round(start_alt, 3), "end", round(last_alt, 3), "delta", round(last_alt - start_alt, 3))

if last_servo:
    print("SERVO_RESULT", *last_servo)
PY

echo "--- console tail (${MODE}) ---"
tail -40 "$LOG"
