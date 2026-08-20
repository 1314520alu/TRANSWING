#!/usr/bin/env bash
# Legacy entry point — delegates to restart_transwing_sitl.sh (fresh EEPROM + MAVProxy).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export DETACH=1
exec bash "$SCRIPT_DIR/restart_transwing_sitl.sh" "${PROFILE:-control}"
