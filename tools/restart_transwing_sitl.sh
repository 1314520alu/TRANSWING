#!/usr/bin/env bash
# Clean-restart Transwing SITL with fresh EEPROM and selectable param profile.
#
# Usage (from Windows PowerShell):
#   wsl bash /mnt/c/Users/alu/Desktop/TRANSWING/tools/restart_transwing_sitl.sh
#   wsl bash /mnt/c/Users/alu/Desktop/TRANSWING/tools/restart_transwing_sitl.sh observe
#   wsl bash /mnt/c/Users/alu/Desktop/TRANSWING/tools/restart_transwing_sitl.sh control
#
# Environment:
#   PROFILE=observe|control   Lua observe-only vs motor takeover (default: control)
#   MP_PORT=14550             Mission Planner UDP port
#   FRESH=1                   Clear eeprom + mav.parm (default: 1)
#   NO_START=1                Stop only, do not start SITL
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRANSWING_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

ARDUPILOT_DIR="${ARDUPILOT_DIR:-$HOME/ardupilot}"
ARDUPILOT_VENV="${ARDUPILOT_VENV:-$HOME/venv-ardupilot}"
RUN_DIR="${RUN_DIR:-transwing_dynamic_mp}"
MP_PORT="${MP_PORT:-14550}"
LOG_FILE="${LOG_FILE:-/tmp/transwing_sitl_restart.log}"
PID_FILE="${PID_FILE:-/tmp/transwing_sitl.pid}"
FRESH="${FRESH:-1}"

PROFILE="${1:-${PROFILE:-control}}"
case "$PROFILE" in
  observe|obs|0)
    PROFILE=observe
    PARAM_SRC="$TRANSWING_ROOT/transwing_sitl_observe.params"
    ;;
  control|ctrl|2)
    PROFILE=control
    PARAM_SRC="$TRANSWING_ROOT/transwing_sitl_mp.params"
    ;;
  *)
    echo "Unknown profile: $PROFILE (use observe or control)" >&2
    exit 1
    ;;
esac

WINDOWS_HOST="${WINDOWS_HOST:-$(awk '/nameserver/ { print $2; exit }' /etc/resolv.conf)}"
WSL_GATEWAY="${WSL_GATEWAY:-$(ip route show 2>/dev/null | awk '/default/ { print $3; exit }')}"

if [[ -f "$ARDUPILOT_VENV/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ARDUPILOT_VENV/bin/activate"
fi

RUN_PATH="$ARDUPILOT_DIR/ArduPlane/$RUN_DIR"
PARAM_DEST="$RUN_PATH/transwing_sitl_active.params"
LUA_SRC="$TRANSWING_ROOT/scripts/transwing_dynamic_mix.lua"

stop_sitl() {
  echo "Stopping existing SITL / MAVProxy..."
  pkill -f "sim_vehicle.py.*quadplane-transwing.*${RUN_DIR}" 2>/dev/null || true
  pkill -f "arduplane.*quadplane-transwing" 2>/dev/null || true
  pkill -f "mavproxy.py.*5760" 2>/dev/null || true
  sleep 2
}

prepare_run_dir() {
  mkdir -p "$RUN_PATH/APM/scripts" "$RUN_PATH/scripts" "$RUN_PATH/logs"
  cp "$LUA_SRC" "$RUN_PATH/APM/scripts/transwing_dynamic_mix.lua"
  cp "$LUA_SRC" "$RUN_PATH/scripts/transwing_dynamic_mix.lua"
  cp "$PARAM_SRC" "$PARAM_DEST"
  cp "$PARAM_SRC" "$RUN_PATH/transwing_sitl_mp.params"

  if [[ "$FRESH" == "1" ]]; then
    echo "Clearing persisted params (eeprom.bin, mav.parm)..."
    rm -f "$RUN_PATH/eeprom.bin" "$RUN_PATH/mav.parm" "$RUN_PATH/mav.tlog" "$RUN_PATH/mav.tlog.raw"
  fi
}

start_sitl() {
  cd "$ARDUPILOT_DIR/ArduPlane"
  : >"$LOG_FILE"

  echo "Starting SITL (profile=$PROFILE)..."
  nohup ../Tools/autotest/sim_vehicle.py \
    -v ArduPlane \
    -f quadplane-transwing \
    --use-dir "$RUN_DIR" \
    --add-param-file "$PARAM_DEST" \
    --no-rebuild \
    --no-mavproxy \
    >>"$LOG_FILE" 2>&1 &
  sv_pid=$!
  echo "$sv_pid" >"$PID_FILE"

  echo -n "Waiting for heartbeat"
  ready=0
  for _ in $(seq 1 90); do
    if python3 - <<'PY' 2>/dev/null; then
from pymavlink import mavutil
c = mavutil.mavlink_connection("tcp:127.0.0.1:5760")
c.wait_heartbeat(timeout=2)
PY
      ready=1
      break
    fi
    echo -n "."
    sleep 1
  done
  if [[ "$ready" == "1" ]]; then
    echo " OK"
  else
    echo " FAILED"
    echo "See log: $LOG_FILE" >&2
    tail -30 "$LOG_FILE" >&2 || true
    exit 1
  fi
}

start_mavproxy() {
  MP_OUTS=(--out="udp:127.0.0.1:${MP_PORT}" --out="udp:${WINDOWS_HOST}:${MP_PORT}")
  if [[ -n "${WSL_GATEWAY:-}" && "${WSL_GATEWAY}" != "${WINDOWS_HOST}" ]]; then
    MP_OUTS+=(--out="udp:${WSL_GATEWAY}:${MP_PORT}")
  fi

  echo "Starting MAVProxy (UDP ${MP_PORT} -> 127.0.0.1 + ${WINDOWS_HOST})..."
  nohup mavproxy.py \
    --daemon \
    --retries=5 \
    --master=tcp:127.0.0.1:5760 \
    --sitl=127.0.0.1:5501 \
    "${MP_OUTS[@]}" \
    >>"$LOG_FILE" 2>&1 &
  mp_pid=$!
  echo "$mp_pid" >>"$PID_FILE"
  sleep 2
}

wait_for_lua() {
  echo -n "Waiting for Lua TW-DYNMIX via MAVLink"
  if python3 "$TRANSWING_ROOT/tools/wait_for_tw_lua.py" "tcp:127.0.0.1:5760" 90; then
    echo " OK"
    sleep 1
    return 0
  fi
  echo " timeout (will still try param apply)"
  return 1
}

apply_tw_params() {
  echo "Applying TW_* params (before MAVProxy, while SITL link is exclusive)..."
  if python3 "$TRANSWING_ROOT/tools/apply_tw_params.py" "$PARAM_DEST" "tcp:127.0.0.1:5760"; then
    echo "TW_* params applied."
    return 0
  fi
  echo "WARNING: TW_* param apply failed; set TW_MIX_MODE manually in MP" >&2
  return 1
}

wait_for_mix_mode() {
  local expected="$1"
  echo -n "Waiting for TW_MIX_MODE=${expected}"
  if python3 "$TRANSWING_ROOT/tools/wait_for_tw_lua.py" "tcp:127.0.0.1:5760" 30 "$expected"; then
    echo " OK"
    return 0
  fi
  echo " timeout"
  return 1
}

verify_boot() {
  echo
  echo "=== Boot check ==="
  if python3 "$TRANSWING_ROOT/tools/read_sitl_params.py" "tcp:127.0.0.1:5760" 2>/dev/null | tee /tmp/transwing_boot_params.txt | grep -q "TW_MIX_MODE"; then
    if grep -q "TW_ENABLE.*1" /tmp/transwing_boot_params.txt 2>/dev/null; then
      echo "  Lua script: loaded"
    else
      echo "  Lua script: TW_ENABLE missing"
    fi
    mix_val="$(awk '/^TW_MIX_MODE/ { print $2 }' /tmp/transwing_boot_params.txt)"
    if [[ "$PROFILE" == "observe" && "$mix_val" == "0.0" ]]; then
      echo "  Lua mix mode: verified (0)"
    elif [[ "$PROFILE" == "control" && "$mix_val" == "2.0" ]]; then
      echo "  Lua mix mode: verified (2)"
    else
      echo "  Lua mix mode: TW_MIX_MODE=${mix_val:-missing}"
    fi
  else
    echo "  Lua script: param read failed"
  fi
  if grep -q "Loaded Transwing QuadPlane SITL dynamic geometry" "$LOG_FILE" 2>/dev/null; then
    echo "  C++ geometry: OK"
  else
    echo "  C++ geometry: check log after boot completes"
  fi
  echo "  Param file: $PARAM_SRC"
  echo "  Active copy: $PARAM_DEST"
  echo "  Motor mix: Q_FRAME_CLASS=17 + TW_MIX_MODE=2 uses Motors_dynamic"
  echo "  Fixes applied:"
  echo "    - Fresh EEPROM (no stale TW_MIX_MODE=0)"
  echo "    - AIRSPEED_MIN/ARSPD_FBW_MIN=19, TRIM_ARSP_CM=2500, AIRSPEED_MAX=31"
  echo "    - Q_ASSIST_SPEED=16 (19-3 m/s stall assist)"
  echo "    - TW_ASST_EN=1 links Q assist to fold hold + Lua mix theta"
  echo "    - RC_OVERRIDE_TIME=10 (RC override lasts 10s)"
}

print_usage() {
  local mix_hint="2"
  if [[ "$PROFILE" == "observe" ]]; then
    mix_hint="0"
  fi
  cat <<EOF

=== Transwing SITL ready ===
Mission Planner: UDP port ${MP_PORT}
Log: ${LOG_FILE}

--- Recommended test sequence ---
1. Connect MP (UDP ${MP_PORT}), wait for GPS/EKF green
2. Mode QSTABILIZE -> Arm -> wait SERVO11 ~1000 (fold vertical)
3. Throttle up (see RC section below) until airspeed > 13 m/s
4. Switch FBWB (not FBWA) for transition; never transition at 0 m/s
5. MP messages should show TW-DYNMIX: running mix_mode=${mix_hint}

--- WSL 交互控制台 (MAVProxy) ---
  bash ${TRANSWING_ROOT}/tools/wsl_control_console.sh
  # Windows 新终端:
  # powershell -File ${TRANSWING_ROOT}/tools/wsl_control_console.ps1

--- RC3 throttle (另开 WSL 终端，勿在 MAVProxy 里跑 bash) ---
  # one shot:
  bash ${TRANSWING_ROOT}/tools/send_rc.sh 3 1700
  # hold 15s climb:
  bash ${TRANSWING_ROOT}/tools/rc_throttle_hold.sh 1700 15

--- MAVProxy (separate WSL terminal, wait for link 1 OK) ---
  mavproxy.py --master=tcp:127.0.0.1:5760
  rc 3 1700

--- Stop SITL ---
  NO_START=1 bash ${TRANSWING_ROOT}/tools/restart_transwing_sitl.sh

EOF
}

stop_sitl
if [[ "${NO_START:-0}" == "1" ]]; then
  echo "Stopped. NO_START=1, not restarting."
  exit 0
fi

prepare_run_dir
start_sitl
wait_for_lua || true
apply_tw_params || true
if [[ "$PROFILE" == "observe" ]]; then
  wait_for_mix_mode 0 || true
else
  wait_for_mix_mode 2 || true
fi
verify_boot
start_mavproxy
print_usage
