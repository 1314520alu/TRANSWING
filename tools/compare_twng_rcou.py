#!/usr/bin/env python3
"""Compare Lua dynamic mix (TWNG) against ArduPilot motor outputs (RCOU)."""

from __future__ import annotations

import argparse
import math
import sys
from collections import defaultdict
from pathlib import Path

try:
    from pymavlink import DFReader
except ImportError as exc:  # pragma: no cover - runtime dependency
    raise SystemExit("pymavlink is required: pip install pymavlink") from exc


FOLD_BUCKETS = (
    (82.5, 90.0, "90"),
    (52.5, 67.5, "60"),
    (37.5, 52.5, "45"),
    (0.0, 22.5, "0"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="ArduPilot DataFlash .BIN log")
    parser.add_argument(
        "--tolerance-us",
        type=int,
        default=50_000,
        help="Max TimeUS gap when pairing TWNG with RCOU (default: 50000)",
    )
    return parser.parse_args()


def bucket_for_theta(theta: float) -> str | None:
    for low, high, label in FOLD_BUCKETS:
        if low <= theta <= high:
            return label
    return None


def read_messages(log_path: Path):
    reader = DFReader.DFReader_binary(str(log_path))
    twng = []
    rcou = []
    while True:
        msg = reader.recv_msg()
        if msg is None:
            break
        msg_type = msg.get_type()
        if msg_type == "TWNG":
            twng.append(msg)
        elif msg_type == "RCOU":
            rcou.append(msg)
    return twng, rcou


def motor_fields(msg) -> tuple[float, float, float, float] | None:
    if all(hasattr(msg, field) for field in ("M1", "M2", "M3", "M4")):
        return float(msg.M1), float(msg.M2), float(msg.M3), float(msg.M4)
    return None


def actual_fields(msg) -> tuple[float, float, float, float] | None:
    if all(hasattr(msg, field) for field in ("A1", "A2", "A3", "A4")):
        return float(msg.A1), float(msg.A2), float(msg.A3), float(msg.A4)
    return None


def rcou_fields(msg) -> tuple[float, float, float, float] | None:
    if all(hasattr(msg, field) for field in ("C1", "C2", "C3", "C4")):
        return float(msg.C1), float(msg.C2), float(msg.C3), float(msg.C4)
    return None


def nearest_rcou(time_us: int, rcou_rows, tolerance_us: int):
    best = None
    best_dt = tolerance_us + 1
    for row in rcou_rows:
        dt = abs(int(row.TimeUS) - time_us)
        if dt < best_dt:
            best_dt = dt
            best = row
    if best is None or best_dt > tolerance_us:
        return None
    return best


def pwm_delta(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> list[float]:
    return [abs(x - y) for x, y in zip(a, b)]


def summarize(deltas: list[float]) -> tuple[float, float]:
    if not deltas:
        return 0.0, 0.0
    return sum(deltas) / len(deltas), max(deltas)


def main() -> int:
    args = parse_args()
    if not args.log.is_file():
        print(f"Log not found: {args.log}", file=sys.stderr)
        return 1

    twng_rows, rcou_rows = read_messages(args.log)
    if not twng_rows:
        print("No TWNG messages found.", file=sys.stderr)
        return 1

    has_actual = any(actual_fields(row) is not None for row in twng_rows)
    paired = 0
    bucket_lua_ap = defaultdict(list)
    bucket_lua_rcou = defaultdict(list)
    all_lua_ap = []
    all_lua_rcou = []

    for row in twng_rows:
        lua_pwm = motor_fields(row)
        if lua_pwm is None:
            continue
        est = float(getattr(row, "Est", float("nan")))
        bucket = bucket_for_theta(est)

        if has_actual:
            ap_pwm = actual_fields(row)
            if ap_pwm is not None:
                deltas = pwm_delta(lua_pwm, ap_pwm)
                all_lua_ap.extend(deltas)
                if bucket is not None:
                    bucket_lua_ap[bucket].extend(deltas)
                paired += 1

        rcou = nearest_rcou(int(row.TimeUS), rcou_rows, args.tolerance_us)
        if rcou is not None:
            rcou_pwm = rcou_fields(rcou)
            if rcou_pwm is not None:
                deltas = pwm_delta(lua_pwm, rcou_pwm)
                all_lua_rcou.extend(deltas)
                if bucket is not None:
                    bucket_lua_rcou[bucket].extend(deltas)

    print(f"TWNG rows: {len(twng_rows)}")
    print(f"RCOU rows: {len(rcou_rows)}")
    print(f"TWNG with A1-A4: {'yes' if has_actual else 'no'}")

    if all_lua_ap:
        mean_delta, max_delta = summarize(all_lua_ap)
        print(f"\nLua vs TWNG A1-A4 (all motors): mean |Δ|={mean_delta:.1f} max |Δ|={max_delta:.1f}")
        for label, _, _ in FOLD_BUCKETS:
            deltas = bucket_lua_ap.get(label, [])
            if not deltas:
                continue
            mean_b, max_b = summarize(deltas)
            print(f"  fold ~{label}°: mean |Δ|={mean_b:.1f} max |Δ|={max_b:.1f} samples={len(deltas) // 4}")

    if all_lua_rcou:
        mean_delta, max_delta = summarize(all_lua_rcou)
        print(f"\nLua vs RCOU C1-C4 (all motors): mean |Δ|={mean_delta:.1f} max |Δ|={max_delta:.1f}")
        for label, _, _ in FOLD_BUCKETS:
            deltas = bucket_lua_rcou.get(label, [])
            if not deltas:
                continue
            mean_b, max_b = summarize(deltas)
            print(f"  fold ~{label}°: mean |Δ|={mean_b:.1f} max |Δ|={max_b:.1f} samples={len(deltas) // 4}")

    if not all_lua_ap and not all_lua_rcou:
        print("No comparable motor PWM pairs found.", file=sys.stderr)
        return 1

    if has_actual and paired == 0:
        print("Warning: TWNG lacks populated A1-A4 fields.", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
