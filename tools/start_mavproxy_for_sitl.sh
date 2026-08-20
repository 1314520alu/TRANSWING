#!/usr/bin/env bash
set -euo pipefail

MP_PORT="${MP_PORT:-14550}"
LOG_FILE="${LOG_FILE:-/tmp/transwing_dynamic_sitl.log}"
ARDUPILOT_VENV="${ARDUPILOT_VENV:-$HOME/venv-ardupilot}"

if [[ -f "$ARDUPILOT_VENV/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ARDUPILOT_VENV/bin/activate"
fi

WINDOWS_HOST="${WINDOWS_HOST:-$(awk '/nameserver/ { print $2; exit }' /etc/resolv.conf)}"
WSL_GATEWAY="${WSL_GATEWAY:-$(ip route show 2>/dev/null | awk '/default/ { print $3; exit }')}"

pkill -f "mavproxy.py.*${MP_PORT}" 2>/dev/null || true
sleep 1

OUTS=(--out="udp:127.0.0.1:${MP_PORT}" --out="udp:${WINDOWS_HOST}:${MP_PORT}")
if [[ -n "${WSL_GATEWAY}" && "${WSL_GATEWAY}" != "${WINDOWS_HOST}" ]]; then
  OUTS+=(--out="udp:${WSL_GATEWAY}:${MP_PORT}")
fi

nohup mavproxy.py \
  --daemon \
  --retries=5 \
  --master=tcp:127.0.0.1:5760 \
  --sitl=127.0.0.1:5501 \
  "${OUTS[@]}" \
  >>"$LOG_FILE" 2>&1 &

sleep 2
if pgrep -f "mavproxy.py.*${MP_PORT}" >/dev/null 2>&1; then
  echo "MAVProxy running (UDP ${MP_PORT})"
  pgrep -af mavproxy | grep -v pgrep
else
  echo "MAVProxy failed; use Mission Planner TCP 127.0.0.1:5760"
  exit 1
fi
