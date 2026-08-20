#!/usr/bin/env python3
"""Wait until transwing_dynamic_mix.lua registers TW_* params or sends STATUSTEXT."""

import sys
import time
from pathlib import Path

from pymavlink import mavutil

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mavlink_util import param_name, status_text


def main():
    endpoint = sys.argv[1] if len(sys.argv) > 1 else "tcp:127.0.0.1:5760"
    timeout = float(sys.argv[2]) if len(sys.argv) > 2 else 90.0
    expect_mix = sys.argv[3] if len(sys.argv) > 3 else ""

    conn = mavutil.mavlink_connection(endpoint, source_system=255)
    conn.wait_heartbeat(timeout=min(timeout, 30))
    sys_id = conn.target_system or 1
    comp_id = conn.target_component or 1
    if sys_id == 0:
        sys_id = 1

    deadline = time.time() + timeout
    loaded = False
    mix_ok = not expect_mix

    while time.time() < deadline:
        conn.mav.param_request_read_send(sys_id, comp_id, b"TW_MIX_MODE", -1)
        msg = conn.recv_match(blocking=True, timeout=1)
        if msg is not None:
            mtype = msg.get_type()
            if mtype == "PARAM_VALUE":
                key = param_name(msg)
                if key == "TW_MIX_MODE":
                    loaded = True
                    if expect_mix and abs(msg.param_value - float(expect_mix)) < 0.01:
                        mix_ok = True
            elif mtype == "STATUSTEXT":
                text = status_text(msg)
                if "TW-DYNMIX: loaded" in text:
                    loaded = True
                if expect_mix and f"mix_mode={expect_mix}" in text:
                    mix_ok = True

        if loaded and mix_ok:
            print(f"Lua ready on {endpoint}")
            if expect_mix:
                print(f"TW_MIX_MODE verified: {expect_mix}")
            return 0

    if not loaded:
        print("ERROR: TW_MIX_MODE / TW-DYNMIX not seen before timeout", file=sys.stderr)
    elif expect_mix:
        print(f"ERROR: TW_MIX_MODE != {expect_mix} before timeout", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
