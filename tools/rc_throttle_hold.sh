#!/usr/bin/env bash
# Hold RC3 throttle override for N seconds (ArduPilot override expires ~RC_OVERRIDE_TIME).
# Usage: rc_throttle_hold.sh [pwm] [seconds]
# Example: rc_throttle_hold.sh 1700 15
set -euo pipefail

PWM="${1:-1700}"
SECONDS="${2:-15}"
INTERVAL="${INTERVAL:-0.4}"

ARDUPILOT_VENV="${ARDUPILOT_VENV:-$HOME/venv-ardupilot}"
if [[ -f "$ARDUPILOT_VENV/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ARDUPILOT_VENV/bin/activate"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
END=$((SECONDS * 10 / 4))
echo "RC3 hold ${PWM} for ~${SECONDS}s (every ${INTERVAL}s)"
for _ in $(seq 1 "$END"); do
  bash "$SCRIPT_DIR/send_rc.sh" 3 "$PWM"
  sleep "$INTERVAL"
done
echo "Done."
