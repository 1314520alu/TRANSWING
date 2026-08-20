#!/usr/bin/env python3
import sys
from pymavlink import mavutil

log = sys.argv[1] if len(sys.argv) > 1 else (
    "/home/alu/ardupilot/ArduPlane/transwing_dynamic_mp/logs/00000019.BIN"
)
start = float(sys.argv[2]) if len(sys.argv) > 2 else 397.5
end = float(sys.argv[3]) if len(sys.argv) > 3 else 400.5

ml = mavutil.mavlink_connection(log)
while True:
    m = ml.recv_match(type=["TWNG", "RCOU", "MODE"], blocking=False)
    if m is None:
        break
    ts = m.TimeUS / 1e6
    if ts < start or ts > end:
        continue
    if m.get_type() == "TWNG":
        print(
            f"{ts:7.2f}s TWNG Lua M={m.M1:.0f},{m.M2:.0f},{m.M3:.0f},{m.M4:.0f} "
            f"AP A={m.A1:.0f},{m.A2:.0f},{m.A3:.0f},{m.A4:.0f} "
            f"Targ={m.Targ:.1f} Est={m.Est:.1f}"
        )
    elif m.get_type() == "RCOU":
        print(f"{ts:7.2f}s RCOU {m.C1},{m.C2},{m.C3},{m.C4}")
    elif m.get_type() == "MODE":
        print(f"{ts:7.2f}s MODE change")
