#!/usr/bin/env python3
"""Apply TW_* params from a .params file after Lua script has registered them."""

import sys
import time
from pathlib import Path

from pymavlink import mavutil

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mavlink_util import param_name

VERIFY_KEYS = ("TW_MIX_MODE", "TW_LOG_ONLY", "TW_BLEND_AS", "TW_BLEND_MIN", "TW_ATT_ABORT", "TW_ASST_EN", "Q_TILT_MAX")

# Applied after Lua registers TW_*; must match transwing_sitl_mp.params tilt/transition gates.
# Material-optimized: TW_BLEND_AS=11, TW_FW_AS=15 (stall≈15),
# AIRSPEED_MIN/ARSPD_FBW_MIN=15, Q_ASSIST_SPEED=12, cruise=20, AIRSPEED_MAX=30.
EXTRA_PARAM_PREFIXES = ("Q_TILT_", "Q_TRANSITION_", "AIRSPEED_", "ARSPD_", "TRIM_ARSP_", "ROLL_LIMIT_")


def load_tw_params(path):
    params = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "," not in line:
                continue
            name, value = line.split(",", 1)
            name = name.strip()
            if name.startswith("TW_") or name.startswith(EXTRA_PARAM_PREFIXES):
                params[name] = float(value.strip())
    return params


def drain_messages(conn, seconds=0.3):
    deadline = time.time() + seconds
    while time.time() < deadline:
        conn.recv_match(blocking=False)


def wait_for_param(conn, sys_id, comp_id, name, timeout=90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        conn.mav.param_request_read_send(sys_id, comp_id, name.encode(), -1)
        msg = conn.recv_match(type="PARAM_VALUE", blocking=True, timeout=2)
        if msg is None:
            continue
        key = param_name(msg)
        if key == name:
            return msg.param_value
    return None


def set_param(conn, sys_id, comp_id, name, value, retries=5):
    got_val = None
    msg = None
    for _ in range(retries):
        drain_messages(conn)
        conn.mav.param_set_send(
            sys_id,
            comp_id,
            name.encode(),
            value,
            mavutil.mavlink.MAV_PARAM_TYPE_REAL32,
        )
        time.sleep(0.2)
        conn.mav.param_request_read_send(sys_id, comp_id, name.encode(), -1)
        deadline = time.time() + 4
        while time.time() < deadline:
            msg = conn.recv_match(type="PARAM_VALUE", blocking=True, timeout=1)
            if msg is None:
                continue
            key = param_name(msg)
            if key != name:
                continue
            got_val = msg.param_value
            if abs(got_val - value) < 0.01:
                return True, got_val
            break
    return False, got_val if msg else None


def main():
    param_file = sys.argv[1] if len(sys.argv) > 1 else ""
    endpoint = sys.argv[2] if len(sys.argv) > 2 else "tcp:127.0.0.1:5760"
    if not param_file:
        print("Usage: apply_tw_params.py <file.params> [mavlink-endpoint]", file=sys.stderr)
        return 1

    tw = load_tw_params(param_file)
    if not tw:
        print(f"No TW_* / Q_TILT_* entries in {param_file}", file=sys.stderr)
        return 1

    conn = mavutil.mavlink_connection(endpoint, source_system=255)
    conn.wait_heartbeat(timeout=15)
    sys_id = conn.target_system or 1
    comp_id = conn.target_component or 1
    if sys_id == 0:
        sys_id = 1

    print(f"Waiting for Lua TW_MIX_MODE on {endpoint} (sys={sys_id})...")
    current = wait_for_param(conn, sys_id, comp_id, "TW_MIX_MODE")
    if current is None:
        print("ERROR: TW_MIX_MODE not registered; is transwing_dynamic_mix.lua loaded?", file=sys.stderr)
        return 1
    print(f"  TW_MIX_MODE currently {current}")

    print(f"Applying {len(tw)} params from {param_file}")
    failures = []
    for name, value in sorted(tw.items()):
        ok, got_val = set_param(conn, sys_id, comp_id, name, value)
        if ok:
            print(f"  {name} = {got_val}")
        else:
            failures.append(name)
            print(f"  WARNING: {name} wanted {value}, got {got_val if got_val is not None else 'no ack'}")

    got = {}
    for name in VERIFY_KEYS:
        if name not in tw:
            continue
        val = wait_for_param(conn, sys_id, comp_id, name, timeout=10)
        if val is not None:
            got[name] = val

    print("Verified:")
    verify_failed = False
    for name in VERIFY_KEYS:
        if name not in tw:
            continue
        expected = tw[name]
        actual = got.get(name)
        if actual is not None and abs(actual - expected) < 0.01:
            print(f"  {name} = {actual}")
        else:
            verify_failed = True
            print(
                f"  {name} = {actual if actual is not None else 'MISSING'} "
                f"(expected {expected})",
                file=sys.stderr,
            )

    conn.mav.command_long_send(
        sys_id,
        comp_id,
        mavutil.mavlink.MAV_CMD_PREFLIGHT_STORAGE,
        0,
        1,
        0, 0, 0, 0, 0, 0,
    )
    print("Params saved to EEPROM.")

    if failures or verify_failed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
