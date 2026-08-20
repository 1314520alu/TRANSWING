#!/usr/bin/env python3
"""Analyze Transwing log for fold stuck at PWM 1500 / 45deg."""
import statistics
import sys
from pathlib import Path

from pymavlink import mavutil

log = sys.argv[1] if len(sys.argv) > 1 else str(
    Path.home() / "ardupilot/ArduPlane/transwing_dynamic_mp/logs/00000021.BIN"
)
ml = mavutil.mavlink_connection(log)

twtr = []
rcou_fold = []
pvals = {}
msgs = []

while True:
    m = ml.recv_match(blocking=False)
    if m is None:
        break
    t = m.get_type()
    if t == "TWTR":
        twtr.append({
            "ts": m.TimeUS / 1e6,
            "Targ": m.Targ,
            "Est": m.Est,
            "Allow": m.Allow,
            "AS": m.AS,
            "Act": int(m.Act),
            "Risk": int(m.Risk),
        })
    elif t == "RCOU":
        c11 = getattr(m, "C11", None)
        if c11 and c11 > 800:
            rcou_fold.append((m.TimeUS / 1e6, c11))
    elif t == "MSG":
        text = m.Message if isinstance(m.Message, str) else m.Message.decode(errors="replace")
        if any(k in text for k in ("TW-DYNMIX", "Transition", "guard", "Tilt", "Q_TILT")):
            msgs.append((m.TimeUS / 1e6, text[:140]))
    elif t == "PARM" and m.Name in (
        "TW_BLEND_MIN", "TW_ACCEL_MIN", "Q_TILT_MAX", "TW_FW_AS", "TW_BLEND_AS"
    ):
        pvals[m.Name] = m.Value

print(f"Log: {log}")
print("=== Params seen in log ===")
for k, v in sorted(pvals.items()):
    print(f"  {k} = {v}")

print("\n=== Key messages ===")
for ts, text in msgs[:25]:
    print(f"  {ts:7.1f}s {text}")

bins = {"1450-1550": 0, "1550-1650": 0, "1250-1450": 0, "other": 0}
for _ts, pwm in rcou_fold:
    if 1450 <= pwm <= 1550:
        bins["1450-1550"] += 1
    elif 1550 < pwm <= 1650:
        bins["1550-1650"] += 1
    elif 1250 <= pwm < 1450:
        bins["1250-1450"] += 1
    else:
        bins["other"] += 1
print("\n=== SERVO11 (C11) PWM distribution ===")
for k, v in bins.items():
    print(f"  {k}: {v} samples")

near45 = [r for r in twtr if abs(r["Est"] - 45) < 3 or abs(r["Targ"] - 45) < 3]
hold = [r for r in twtr if r["Act"] != 0]
print(f"\n=== TWTR summary (n={len(twtr)}) ===")
print(f"  samples Est/Targ~45deg: {len(near45)}")
print(f"  non-ALLOW actions: {len(hold)}")
if near45:
    as_vals = [r["AS"] for r in near45]
    print(
        f"  At ~45deg airspeed: min={min(as_vals):.1f} "
        f"max={max(as_vals):.1f} mean={statistics.mean(as_vals):.1f}"
    )
    allows = sorted({round(r["Allow"], 1) for r in near45})
    print(f"  Allow values at ~45deg: {allows}")

print("\n=== Last 15 non-ALLOW TWTR ===")
for r in hold[-15:]:
    print(
        f"  {r['ts']:7.1f}s T={r['Targ']:5.1f} E={r['Est']:5.1f} "
        f"Allow={r['Allow']:5.1f} AS={r['AS']:5.1f} act={r['Act']} risk={r['Risk']}"
    )

print("\n=== Last 20 TWTR ===")
for r in twtr[-20:]:
    print(
        f"  {r['ts']:7.1f}s T={r['Targ']:5.1f} E={r['Est']:5.1f} "
        f"Allow={r['Allow']:5.1f} AS={r['AS']:5.1f} act={r['Act']}"
    )

stuck = [(ts, pwm) for ts, pwm in rcou_fold if 1490 <= pwm <= 1510]
if stuck:
    print(f"\n=== PWM 1490-1510: {len(stuck)} samples ===")
    print(
        f"  first={stuck[0][0]:.1f}s last={stuck[-1][0]:.1f}s "
        f"duration~{stuck[-1][0] - stuck[0][0]:.1f}s"
    )
    step = max(1, len(stuck) // 6)
    for ts, pwm in stuck[::step][:8]:
        if not twtr:
            break
        nearest = min(twtr, key=lambda r: abs(r["ts"] - ts))
        if abs(nearest["ts"] - ts) < 3:
            print(
                f"  {ts:.1f}s PWM={pwm} TWTR T={nearest['Targ']:.1f} "
                f"E={nearest['Est']:.1f} Allow={nearest['Allow']:.1f} "
                f"AS={nearest['AS']:.1f} act={nearest['Act']}"
            )
