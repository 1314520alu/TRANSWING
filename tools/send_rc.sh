#!/usr/bin/env bash
# Send RC override from bash (equivalent to MAVProxy "rc N PWM").
# Usage: send_rc.sh <channel> <pwm> [channel pwm ...]
# Example: send_rc.sh 3 1600          # throttle up
# Example: send_rc.sh 3 1500 1 1600   # throttle mid + roll right
set -euo pipefail

if [[ $# -lt 2 || $(($# % 2)) -ne 0 ]]; then
  echo "Usage: $0 <channel> <pwm> [channel pwm ...]" >&2
  echo "Example: $0 3 1600" >&2
  exit 1
fi

ARDUPILOT_VENV="${ARDUPILOT_VENV:-$HOME/venv-ardupilot}"
if [[ -f "$ARDUPILOT_VENV/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ARDUPILOT_VENV/bin/activate"
fi

python3 - "$@" <<'PY'
import sys
from pymavlink import mavutil

args = sys.argv[1:]
conn = mavutil.mavlink_connection("tcp:127.0.0.1:5760", source_system=255)
conn.wait_heartbeat(timeout=10)
sys_id = conn.target_system or 1
comp_id = conn.target_component or 1
if sys_id == 0:
    sys_id = 1

channels = [65535] * 8
for i in range(0, len(args), 2):
    ch = int(args[i])
    pwm = int(args[i + 1])
    if ch < 1 or ch > 8:
        raise SystemExit(f"channel must be 1-8, got {ch}")
    channels[ch - 1] = pwm

conn.mav.rc_channels_override_send(
    sys_id,
    comp_id,
    *channels,
)
print("RC override:", " ".join(f"ch{i+1}={channels[i]}" for i in range(8) if channels[i] != 65535))
PY
