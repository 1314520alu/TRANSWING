"""Set SCR + QuadPlane tilt params on FC via MAVLink."""
from __future__ import annotations

import sys
import time

from pymavlink import mavutil

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM36"
BAUD = int(sys.argv[2]) if len(sys.argv) > 2 else 115200

# First-flight / observe phase from Transwing_实机固件与参数配置.md
# Rates: FC only accepts integers; 90deg/19s ≈ 4.74 → use 5
PARAMS = [
    ("SCR_ENABLE", 1),
    ("SCR_HEAP_SIZE", 204800),
    ("Q_ENABLE", 1),
    ("Q_FRAME_CLASS", 1),
    ("Q_FRAME_TYPE", 1),
    ("Q_TILT_ENABLE", 1),
    ("Q_TILT_MASK", 15),
    ("Q_TILT_TYPE", 0),
    ("Q_TILT_MAX", 90),
    ("Q_TILT_RATE_UP", 5),
    ("Q_TILT_RATE_DN", 5),
    ("Q_TILT_FIX_GAIN", 0),
    ("Q_TILT_FIX_ANGLE", 0),
    ("Q_TILT_YAW_ANGLE", 0),
    ("Q_TRANSITION_MS", 25000),
    ("SERVO11_FUNCTION", 41),
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
            return abs(msg.param_value - value) < 0.51 or abs(msg.param_value - value) < 1e-3
    return False


def get_param(m, name: str, timeout: float = 3.0) -> float | None:
    m.mav.param_request_read_send(
        m.target_system, m.target_component, name.encode("ascii"), -1
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
            return float(msg.param_value)
    return None


def main() -> int:
    print(f"Connecting {PORT} @ {BAUD} ...")
    m = mavutil.mavlink_connection(PORT, baud=BAUD, autoreconnect=True)
    hb = m.wait_heartbeat(timeout=15)
    if hb is None:
        print("ERROR: no heartbeat")
        return 1
    print(f"Heartbeat sys={m.target_system} comp={m.target_component}")

    print("\n=== SET ===")
    failed = []
    for name, value in PARAMS:
        ok = set_param(m, name, value)
        status = "OK" if ok else "FAIL/NO ACK"
        print(f"  {status:12} {name}={value}")
        if not ok:
            failed.append(name)
        time.sleep(0.05)

    print("\n=== VERIFY ===")
    for name, expected in PARAMS:
        got = get_param(m, name)
        if got is None:
            print(f"  MISSING      {name}")
            failed.append(name)
        else:
            match = abs(got - expected) < 0.51
            print(f"  {'OK' if match else 'DIFF':12} {name}={got} (want {expected})")
            if not match:
                failed.append(name)

    print("\nNOTE: SCR_ENABLE requires reboot before Lua loads.")
    if failed:
        print("FAILED:", ", ".join(sorted(set(failed))))
        return 2
    print("All params set and verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
