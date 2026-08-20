#!/usr/bin/env python3
"""Read key params from running SITL."""
import sys
import time
from pathlib import Path

from pymavlink import mavutil

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mavlink_util import param_name

PARAMS = [
    "SCR_ENABLE", "Q_ENABLE", "Q_FRAME_CLASS", "Q_FRAME_TYPE",
    "TW_ENABLE", "TW_MIX_MODE", "TW_LOG_ONLY", "TW_BLEND_AS",
    "TW_FW_AS", "TW_ACCEL_MIN", "TW_BLEND_MIN", "TW_ATT_ABORT", "TW_ASST_EN", "TW_GUARD", "TW_INPUT_SRC",
    "Q_TILT_MAX", "Q_TRANSITION_MS",
    "ARSPD_FBW_MIN", "Q_ASSIST_SPEED", "AIRSPEED_MIN", "AIRSPEED_MAX", "TRIM_ARSP_CM", "ROLL_LIMIT_DEG", "Q_TRANSITION_MS",
]


def read_param(conn, sys_id, comp_id, name, timeout=2):
    conn.mav.param_request_read_send(sys_id, comp_id, name.encode(), -1)
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = conn.recv_match(type="PARAM_VALUE", blocking=True, timeout=1)
        if msg is None:
            continue
        key = param_name(msg)
        if key == name:
            return msg.param_value
    return None


def main():
    endpoint = sys.argv[1] if len(sys.argv) > 1 else "tcp:127.0.0.1:5760"
    conn = mavutil.mavlink_connection(endpoint, source_system=255)
    conn.wait_heartbeat(timeout=8)
    sys_id = conn.target_system or 1
    comp_id = conn.target_component or 1
    if sys_id == 0:
        sys_id = 1

    print(f"endpoint: {endpoint}")
    print(f"target: sys={sys_id} comp={comp_id}")
    for name in PARAMS:
        value = read_param(conn, sys_id, comp_id, name)
        print(f"{name:18} {value if value is not None else '(missing)'}")


if __name__ == "__main__":
    main()
