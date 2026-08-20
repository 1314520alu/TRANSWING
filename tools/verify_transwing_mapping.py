#!/usr/bin/env python3
"""Static checks for Transwing SITL channel mapping consistency."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_SERVO_FUNCTIONS = {
    1: 33,
    2: 34,
    3: 35,
    4: 36,
    5: 4,
    6: 4,
    7: 19,
    8: 19,
    9: 21,
    10: 21,
    11: 41,
    13: 94,
    14: 95,
    15: 96,
    16: 97,
}

SURFACE_SERVO_INDICES = (4, 5, 6, 7, 8, 9)
SURFACE_PATCH_MARKERS = (
    "AILERON_SERVO_A",
    "ELEVATOR_SERVO_A",
    "RUDDER_SERVO_A",
    "calculate_transwing_surfaces",
    "build_surface_input",
)
MIRROR_SERVO_INDICES = (12, 13, 14, 15)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--params",
        nargs="*",
        type=Path,
        default=[
            ROOT / "transwing_sitl_startup.params",
            ROOT / "transwing_lua_sitl.params",
            ROOT / "transwing_sitl_mp.params",
        ],
    )
    parser.add_argument(
        "--patch",
        type=Path,
        default=ROOT / "patches" / "ardupilot-transwing-surface-forces.patch",
    )
    parser.add_argument(
        "--lua",
        type=Path,
        default=ROOT / "scripts" / "transwing_dynamic_mix.lua",
    )
    return parser.parse_args()


def parse_param_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "," not in line:
            continue
        key, value = line.split(",", 1)
        values[key.strip()] = value.strip()
    return values


def check_params(paths: list[Path]) -> list[str]:
    errors: list[str] = []
    merged: dict[str, str] = {}
    for path in paths:
        if not path.is_file():
            errors.append(f"missing params file: {path}")
            continue
        merged.update(parse_param_file(path))

    for servo, function in EXPECTED_SERVO_FUNCTIONS.items():
        key = f"SERVO{servo}_FUNCTION"
        actual = merged.get(key)
        if actual is None:
            errors.append(f"{key} not set in params")
        elif int(actual) != function:
            errors.append(f"{key}={actual}, expected {function}")
    return errors


def check_patch(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"missing patch: {path}"]
    text = path.read_text(encoding="utf-8")
    for marker in SURFACE_PATCH_MARKERS:
        if marker not in text:
            errors.append(f"patch missing surface marker: {marker}")
    if "calculate_forces" not in text:
        errors.append("patch does not reference calculate_forces")
    if "calculate_transwing_surfaces" not in text:
        errors.append("patch missing calculate_transwing_surfaces")
    return errors


def check_lua(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"missing lua: {path}"]
    text = path.read_text(encoding="utf-8")
    if not re.search(r"set_output_pwm\(93 \+ i", text):
        errors.append("lua does not mirror to scripting outputs 94-97")
    if "A1,A2,A3,A4" not in text:
        errors.append("lua TWNG log missing A1-A4 actual motor fields")
    if "read_control_inputs" not in text:
        errors.append("lua missing read_control_inputs")
    return errors


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    errors.extend(check_params(args.params))
    errors.extend(check_patch(args.patch))
    errors.extend(check_lua(args.lua))

    if errors:
        print("Transwing mapping verification failed:")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("Transwing mapping verification passed.")
    print(f"  params: {len(args.params)} files")
    print(f"  patch: {args.patch.name}")
    print(f"  lua: {args.lua.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
