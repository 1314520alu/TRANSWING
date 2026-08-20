#!/usr/bin/env python3
"""Parse Transwing BIN log for mode changes and guard abort context."""
import sys
from pymavlink import mavutil

log_path = sys.argv[1] if len(sys.argv) > 1 else (
    "/home/alu/ardupilot/ArduPlane/transwing_dynamic_mp/logs/00000015.BIN"
)

MODE_NAMES = {
    0: "MANUAL", 5: "FBWA", 6: "FBWB", 17: "QSTABILIZE", 18: "QHOVER",
    19: "QLOITER", 20: "QLAND", 21: "QRTL",
}

ml = mavutil.mavlink_connection(log_path)
events = []
while True:
    m = ml.recv_match(blocking=False)
    if m is None:
        break
    t = m.get_type()
    ts = getattr(m, "TimeUS", 0) / 1e6
    if t == "MODE":
        mode = getattr(m, "Mode", None)
        events.append((ts, "MODE", MODE_NAMES.get(mode, str(mode))))
    elif t == "TWTR":
        events.append((ts, "TWTR", {
            "Targ": round(getattr(m, "Targ", 0), 1),
            "Est": round(getattr(m, "Est", 0), 1),
            "AS": round(getattr(m, "AS", 0), 1),
            "Roll": round(getattr(m, "Roll", 0), 1),
            "Pitch": round(getattr(m, "Pitch", 0), 1),
            "Climb": round(getattr(m, "Climb", 0), 1),
            "Sat": getattr(m, "Sat", 0),
            "Risk": int(getattr(m, "Risk", 0)),
            "Act": int(getattr(m, "Act", 0)),
            "Allow": round(getattr(m, "Allow", 0), 1),
        }))
    elif t == "MSG":
        msg = getattr(m, "Message", "") or ""
        if "TW-DYNMIX" in msg:
            events.append((ts, "MSG", msg))

print(f"Log: {log_path}\n")
print("=== Timeline (mode changes + guard messages + non-ALLOW TWTR) ===")
last_twtr = -999
for ts, kind, data in events:
    if kind == "TWTR":
        act = data["Act"]
        if act != 0 or ts - last_twtr >= 2.0:
            print(
                f"{ts:7.1f}s TWTR Targ={data['Targ']:5.1f} Est={data['Est']:5.1f} "
                f"AS={data['AS']:5.1f} pitch={data['Pitch']:5.1f} climb={data['Climb']:5.1f} "
                f"risk={data['Risk']} act={data['Act']} allow={data['Allow']:5.1f}"
            )
            last_twtr = ts
    else:
        print(f"{ts:7.1f}s {kind}: {data}")

print("\n=== ABORT_TO_Q summary (Act=2) ===")
for ts, kind, data in events:
    if kind == "TWTR" and data["Act"] == 2:
        print(f"{ts:7.1f}s {data}")
