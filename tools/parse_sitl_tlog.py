#!/usr/bin/env python3
"""Parse Mission Planner SITL tlog files for Transwing flip/abort analysis."""

import glob
import math
import os
import sys

from pymavlink import mavutil

LOG_DIR = os.environ.get(
    "TRANSWING_TLOG_DIR",
    os.path.expanduser(r"~\Documents\Mission Planner\logs\SITL\FIXED_WING\1"),
)

MODE_NAMES = {
    0: "MANUAL",
    5: "FBWA",
    6: "FBWB",
    16: "RTL",
    17: "QSTABILIZE",
    18: "QHOVER",
    19: "QLOITER",
    20: "QLAND",
    21: "QRTL",
}


def mode_name(mode):
    return MODE_NAMES.get(mode, str(mode))


def nearest_airspeed(airspeeds, t, max_dt=2.0):
    if not airspeeds:
        return None, None
    rel, (aspeed, climb) = min(airspeeds.items(), key=lambda kv: abs(kv[0] - t))
    if abs(rel - t) > max_dt:
        return None, None
    return aspeed, climb


def parse_log(path):
    ml = mavutil.mavlink_connection(path)
    t0 = None
    last_mode = None
    last_servo = None
    max_roll = max_pitch = 0.0
    max_roll_t = max_pitch_t = 0.0
    max_roll_mode = max_pitch_mode = None
    mode_changes = []
    tw_msgs = []
    flip_events = []
    fbwa_max_roll = 0.0
    fbwa_max_roll_t = 0.0
    airspeeds = {}

    while True:
        m = ml.recv_match(blocking=False)
        if m is None:
            break
        t = m.get_type()
        ts = getattr(m, "_timestamp", None)
        if ts is None:
            ts = getattr(m, "time_boot_ms", 0) / 1000.0
        if t0 is None and ts:
            t0 = ts
        rel = (ts - t0) if t0 else ts

        if t == "HEARTBEAT" and getattr(m, "type", 0) == 1:
            mode = getattr(m, "custom_mode", None)
            if mode != last_mode:
                mode_changes.append((rel, mode))
                last_mode = mode
        elif t == "ATTITUDE":
            roll = math.degrees(m.roll)
            pitch = math.degrees(m.pitch)
            if abs(roll) > abs(max_roll):
                max_roll, max_roll_t, max_roll_mode = roll, rel, last_mode
            if abs(pitch) > abs(max_pitch):
                max_pitch, max_pitch_t, max_pitch_mode = pitch, rel, last_mode
            if last_mode == 5 and abs(roll) > abs(fbwa_max_roll):
                fbwa_max_roll = roll
                fbwa_max_roll_t = rel
            if abs(roll) > 45 or abs(pitch) > 60:
                flip_events.append((rel, roll, pitch, last_mode, list(last_servo or [])))
        elif t == "VFR_HUD":
            airspeeds[rel] = (m.airspeed, m.climb)
        elif t == "SERVO_OUTPUT_RAW":
            last_servo = [getattr(m, f"servo{i}_raw", 0) for i in range(1, 13)]
        elif t == "STATUSTEXT":
            txt = m.text or ""
            if any(k in txt for k in ("TW-DYNMIX", "Abort", "ABORT", "PreArm", "Arm:")):
                tw_msgs.append((rel, txt))

    duration = 0.0
    for rel, _ in mode_changes:
        duration = max(duration, rel)
    if flip_events:
        duration = max(duration, flip_events[-1][0])

    fbwa_as, _ = nearest_airspeed(airspeeds, fbwa_max_roll_t)
    abort_msgs = [m for m in tw_msgs if "abort" in m[1].lower()]
    guard_msgs = list(dict.fromkeys(m[1] for m in tw_msgs if "guard reason" in m[1]))

    return {
        "path": path,
        "name": os.path.basename(path),
        "size_mb": os.path.getsize(path) / 1e6,
        "duration": duration,
        "max_roll": max_roll,
        "max_roll_t": max_roll_t,
        "max_roll_mode": max_roll_mode,
        "max_pitch": max_pitch,
        "max_pitch_t": max_pitch_t,
        "fbwa_max_roll": fbwa_max_roll,
        "fbwa_max_roll_t": fbwa_max_roll_t,
        "fbwa_as": fbwa_as,
        "flip_count": len(flip_events),
        "mode_changes": mode_changes,
        "abort_msgs": abort_msgs,
        "guard_msgs": guard_msgs,
        "tw_msgs": tw_msgs,
        "flip_events": flip_events,
        "airspeeds": airspeeds,
    }


def print_summary(results):
    print("=== SITL tlog summary ===")
    header = (
        f"{'log':<30} {'dur':>6} {'max_roll':>9} {'max_pitch':>9} "
        f"{'fbwa_roll':>9} {'flip':>5} {'modes':>6}"
    )
    print(header)
    print("-" * len(header))
    for r in results:
        flip_flag = "YES" if r["flip_count"] else "no"
        print(
            f"{r['name'][:30]:<30} {r['duration']:6.0f}s "
            f"{r['max_roll']:8.1f}d {r['max_pitch']:8.1f}d "
            f"{r['fbwa_max_roll']:8.1f}d {flip_flag:>5} {len(r['mode_changes']):>6}"
        )


def print_detail(r):
    print(f"\n--- {r['name']} ({r['size_mb']:.1f} MB) ---")
    print(
        f"max roll {r['max_roll']:.1f} deg @ {r['max_roll_t']:.1f}s "
        f"mode={mode_name(r['max_roll_mode'])}"
    )
    print(f"max pitch {r['max_pitch']:.1f} deg @ {r['max_pitch_t']:.1f}s")
    if abs(r["fbwa_max_roll"]) > 5:
        print(
            f"FBWA max roll {r['fbwa_max_roll']:.1f} deg @ {r['fbwa_max_roll_t']:.1f}s "
            f"AS={r['fbwa_as']}"
        )

    print("mode changes:")
    for t, m in r["mode_changes"]:
        print(f"  {t:7.1f}s -> {mode_name(m)}")

    if r["abort_msgs"]:
        print("abort messages:")
        for t, txt in r["abort_msgs"][:12]:
            print(f"  {t:7.1f}s {txt}")

    if r["guard_msgs"]:
        print("guard reasons (unique):")
        for g in r["guard_msgs"][:10]:
            print(f"  {g}")

    if r["flip_events"]:
        print(f"flip-like events: {len(r['flip_events'])}")
        for rel, roll, pitch, mode, servos in r["flip_events"][:6]:
            aspeed, climb = nearest_airspeed(r["airspeeds"], rel)
            sv = servos[:8] if servos else []
            print(
                f"  {rel:7.1f}s mode={mode_name(mode):10s} "
                f"roll={roll:6.1f} pitch={pitch:6.1f} AS={aspeed} climb={climb} "
                f"servo1-8={sv}"
            )


def main():
    log_dir = sys.argv[1] if len(sys.argv) > 1 else LOG_DIR
    pattern = os.path.join(log_dir, "*.tlog")
    logs = sorted(glob.glob(pattern))
    if not logs:
        print(f"No tlog files in {log_dir}")
        return 1

    print(f"dir: {log_dir}")
    print(f"files: {len(logs)}\n")

    results = [parse_log(p) for p in logs]
    print_summary(results)

    print("\n=== abnormal logs ===")
    for r in results:
        if r["flip_count"] or abs(r["fbwa_max_roll"]) >= 20 or r["abort_msgs"]:
            print_detail(r)

    return 0


if __name__ == "__main__":
    sys.exit(main())
