"""List APM/scripts on FC via MAVLink FTP (COM port)."""
from __future__ import annotations

import sys

from pymavlink import mavftp, mavutil

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM36"
BAUD = int(sys.argv[2]) if len(sys.argv) > 2 else 115200

# ArduPilot scripting tree + common aliases
TARGETS = [
    "@SCRIPTING",
    "@SCRIPTING/modules",
    "@SCRIPTING/modules/MAVLink",
    "APM/scripts",
    "APM/scripts/modules",
    "APM/scripts/modules/MAVLink",
]

NEEDED = [
    "transwing_dynamic_mix.lua",
    "mavlink_msg_NAMED_VALUE_FLOAT.lua",
    "mavlink_msgs.lua",
]


def main() -> int:
    print(f"Connecting {PORT} @ {BAUD} ...")
    m = mavutil.mavlink_connection(PORT, baud=BAUD, autoreconnect=True)
    hb = m.wait_heartbeat(timeout=15)
    if hb is None:
        print("ERROR: no heartbeat")
        return 1
    print(f"Heartbeat: sys={m.target_system} comp={m.target_component} type={hb.type}")

    ftp = mavftp.MAVFTP(
        m,
        target_system=m.target_system,
        target_component=m.target_component,
    )
    found = {n: [] for n in NEEDED}

    for path in TARGETS:
        print(f"\n=== LIST {path} ===")
        ret = ftp.cmd_list([path])
        print(f"  result: {ret}")
        entries = getattr(ftp, "list_result", None) or []
        if not entries:
            print("  (empty or failed)")
            continue
        for e in entries:
            name = e.name if hasattr(e, "name") else str(e)
            size = getattr(e, "size_b", getattr(e, "size", "?"))
            is_dir = getattr(e, "is_dir", False)
            kind = "DIR" if is_dir else "FILE"
            print(f"  [{kind}] {name}\t{size}")
            for n in NEEDED:
                if name == n:
                    found[n].append(f"{path}/{name} ({size} B)")

    print("\n=== CHECKLIST ===")
    ok_all = True
    for n, locs in found.items():
        if locs:
            print(f"  [OK] {n}")
            for loc in locs:
                print(f"       {loc}")
        else:
            ok_all = False
            print(f"  [MISSING] {n}")
    return 0 if ok_all else 2


if __name__ == "__main__":
    raise SystemExit(main())
