"""Set airspeed / TW_* stall-aligned params on FC via MAVLink.

Material-optimized stall ≈ 15 m/s:
  TW_BLEND_AS=11, TW_FW_AS=15,
  AIRSPEED_MIN=ARSPD_FBW_MIN=15, Q_ASSIST_SPEED=12
"""
from __future__ import annotations

import sys
import time

from pymavlink import mavutil

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM36"
BAUD = int(sys.argv[2] if len(sys.argv) > 2 else 115200)

# AP core stack (newer Plane uses AIRSPEED_* ; ARSPD_FBW_MIN may be absent).
# TW_* only exist after Lua registers the TW_ table — skipped if NO_REPLY.
PARAMS = [
    ("AIRSPEED_MIN", 15),
    ("AIRSPEED_CRUISE", 20),
    ("AIRSPEED_MAX", 30),
    ("Q_ASSIST_SPEED", 12),
    ("ARSPD_FBW_MIN", 15),  # optional / legacy
    ("TW_BLEND_AS", 11),    # requires Lua loaded
    ("TW_FW_AS", 15),       # requires Lua loaded
]


def set_param(m, name: str, value: float, timeout: float = 3.0) -> bool:
    m.mav.param_set_send(
        m.target_system,
        m.target_component,
        name.encode("ascii"),
        float(value),
        mavutil.mavlink.MAV_PARAM_TYPE_REAL32,
    )
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = m.recv_match(type="PARAM_VALUE", blocking=True, timeout=0.5)
        if not msg:
            continue
        pid = msg.param_id
        if isinstance(pid, bytes):
            pid = pid.decode("ascii", "ignore")
        pid = pid.strip("\x00")
        if pid == name:
            ok = abs(float(msg.param_value) - float(value)) < 0.05
            print(f"  {name}={msg.param_value} {'OK' if ok else 'MISMATCH'}")
            return ok
    print(f"  {name} TIMEOUT (no PARAM_VALUE)")
    return False


def main() -> int:
    print(f"Connecting {PORT} @ {BAUD} ...")
    m = mavutil.mavlink_connection(PORT, baud=BAUD)
    m.wait_heartbeat(timeout=15)
    print(f"Heartbeat sys={m.target_system} comp={m.target_component}")
    failed = []
    for name, value in PARAMS:
        if not set_param(m, name, value):
            failed.append(name)
        time.sleep(0.15)
    # Verify read-back
    print("Verify:")
    for name, value in PARAMS:
        m.mav.param_request_read_send(
            m.target_system, m.target_component, name.encode("ascii"), -1
        )
        msg = m.recv_match(type="PARAM_VALUE", blocking=True, timeout=3)
        if msg is None:
            print(f"  {name}: no reply")
            failed.append(name)
            continue
        pid = msg.param_id
        if isinstance(pid, bytes):
            pid = pid.decode("ascii", "ignore")
        print(f"  {pid.strip(chr(0))}={msg.param_value} (want {value})")
    m.close()
    if failed:
        print("FAILED:", ", ".join(sorted(set(failed))))
        return 1
    print("All airspeed params set.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
