#!/usr/bin/env python3
"""Print latest TWTR/TWNG node angle and airspeed from ArduPilot BIN log."""
import glob
import os
import sys
from pathlib import Path

from pymavlink import mavutil

DEFAULT_DIR = Path.home() / "ardupilot/ArduPlane/transwing_dynamic_mp/logs"


def latest_bin(log_dir: Path) -> Path:
    candidates = sorted(log_dir.glob("*.BIN"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError(f"No BIN logs in {log_dir}")
    return candidates[0]


def main() -> None:
    if len(sys.argv) > 1:
        log_path = Path(sys.argv[1])
    else:
        log_path = latest_bin(DEFAULT_DIR)

    ml = mavutil.mavlink_connection(str(log_path))
    twng_last = None
    twtr_last = None
    samples = []

    while True:
        m = ml.recv_match(type=["TWNG", "TWTR"], blocking=False)
        if m is None:
            break
        ts = m.TimeUS / 1e6
        if m.get_type() == "TWNG":
            twng_last = m
        else:
            twtr_last = m
            samples.append(
                (ts, m.Targ, m.Est, m.Allow, m.AS, m.Phase, m.Risk, m.Act, m.Roll, m.Pitch)
            )

    print(f"Log: {log_path}")
    print(f"TWTR rows: {len(samples)}")
    if twtr_last is None:
        print("No TWTR messages found.")
        return

    ts = twtr_last.TimeUS / 1e6
    print(f"\n=== Latest TWTR @ {ts:.2f}s ===")
    print(f"  Targ (target)  = {twtr_last.Targ:.2f} deg")
    print(f"  Est  (estimate)= {twtr_last.Est:.2f} deg")
    print(f"  Allow          = {twtr_last.Allow:.2f} deg")
    print(f"  AS   (airspeed)= {twtr_last.AS:.2f} m/s")
    print(f"  Phase          = {twtr_last.Phase:.0f}")
    print(f"  Risk           = {twtr_last.Risk:.0f}")
    print(f"  Act            = {twtr_last.Act:.0f}")
    print(f"  Roll / Pitch   = {twtr_last.Roll:.1f} / {twtr_last.Pitch:.1f} deg")
    print(f"  Climb          = {twtr_last.Climb:.2f} m/s")

    if twng_last is not None:
        ts = twng_last.TimeUS / 1e6
        print(f"\n=== Latest TWNG @ {ts:.2f}s ===")
        print(
            f"  Targ={twng_last.Targ:.2f} Est={twng_last.Est:.2f} "
            f"Fold_PWM={twng_last.Fold:.0f}"
        )

    print("\n=== Last 10 TWTR samples ===")
    print(f"{'time_s':>8} {'Targ':>7} {'Est':>7} {'Allow':>7} {'AS_m/s':>8} {'Phase':>6} {'Act':>4}")
    for row in samples[-10:]:
        ts, targ, est, allow, aspeed, phase, _risk, act, _roll, _pitch = row
        print(f"{ts:8.2f} {targ:7.2f} {est:7.2f} {allow:7.2f} {aspeed:8.2f} {phase:6.0f} {act:4.0f}")


if __name__ == "__main__":
    main()
