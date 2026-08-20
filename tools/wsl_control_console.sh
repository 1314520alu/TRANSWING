#!/usr/bin/env bash
# Interactive MAVProxy console for Transwing SITL (run inside WSL).
#
# Usage:
#   bash tools/wsl_control_console.sh
#   bash tools/wsl_control_console.sh --no-map
#
# From Windows PowerShell:
#   .\tools\wsl_control_console.ps1
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRANSWING_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ARDUPILOT_VENV="${ARDUPILOT_VENV:-$HOME/venv-ardupilot}"
MASTER="${MASTER:-tcp:127.0.0.1:5760}"
SITL_PORT="${SITL_PORT:-127.0.0.1:5501}"

MAP_ARGS=(--map --console)
if [[ "${1:-}" == "--no-map" ]]; then
  MAP_ARGS=(--console)
fi

if [[ -f "$ARDUPILOT_VENV/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ARDUPILOT_VENV/bin/activate"
fi

if ! python3 - <<'PY' 2>/dev/null; then
from pymavlink import mavutil
mavutil.mavlink_connection("tcp:127.0.0.1:5760").wait_heartbeat(timeout=3)
PY
  echo "SITL not reachable on ${MASTER}." >&2
  echo "Start it first:" >&2
  echo "  bash ${TRANSWING_ROOT}/tools/restart_transwing_sitl.sh control" >&2
  exit 1
fi

cat <<EOF

=== Transwing WSL 控制台 ===
连接: ${MASTER}
常用命令:
  mode QSTABILIZE
  arm throttle
  rc 3 1700          # 油门
  rc 1 1600          # 滚转
  rc 2 1600          # 俯仰
  rc 4 1600          # 偏航
  status
  servo
  param show TW_MIX_MODE

一键脚本（另开终端）:
  bash ${TRANSWING_ROOT}/tools/send_rc.sh 3 1700
  bash ${TRANSWING_ROOT}/tools/rc_throttle_hold.sh 1700 15

退出: Ctrl-D 或输入 exit
EOF

exec mavproxy.py \
  --master="${MASTER}" \
  --sitl="${SITL_PORT}" \
  "${MAP_ARGS[@]}"
