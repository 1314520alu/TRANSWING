import csv
from pathlib import Path


INPUT = Path("transwing_allocation_table.csv")
OUTPUT = Path("transwing_motor_factors.csv")


def normalize_signed(values):
    max_abs = max(abs(v) for v in values) or 1.0
    return [v / max_abs for v in values]


def normalize_throttle(values):
    # Upward thrust in NED has negative dz. Use positive lift factor.
    lift = [-v for v in values]
    max_abs = max(abs(v) for v in lift) or 1.0
    return [v / max_abs for v in lift]


def main():
    rows = list(csv.DictReader(INPUT.open(encoding="utf-8")))
    by_theta = {}
    for row in rows:
        by_theta.setdefault(row["theta_deg"], []).append(row)

    out_rows = []
    for theta, group in sorted(by_theta.items(), key=lambda kv: float(kv[0])):
        group = sorted(group, key=lambda r: r["motor"])
        throttle = normalize_throttle([float(r["vertical_factor_dz"]) for r in group])
        roll = normalize_signed([float(r["roll_moment_x"]) for r in group])
        pitch = normalize_signed([float(r["pitch_moment_y"]) for r in group])
        # Force-vector yaw is included for visibility, drag yaw sign follows the CCW/CW table.
        yaw_force = normalize_signed([float(r["yaw_moment_z_from_force"]) for r in group])
        yaw_drag = normalize_signed([float(r["yaw_drag_sign"]) for r in group])

        for idx, row in enumerate(group):
            out_rows.append(
                {
                    "theta_deg": theta,
                    "motor": row["motor"],
                    "test_letter": row["test_letter"],
                    "physical_position": row["physical_position"],
                    "spin": row["spin"],
                    "throttle_factor": throttle[idx],
                    "roll_factor": roll[idx],
                    "pitch_factor": pitch[idx],
                    "yaw_force_factor": yaw_force[idx],
                    "yaw_drag_factor": yaw_drag[idx],
                }
            )

    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        fields = [
            "theta_deg",
            "motor",
            "test_letter",
            "physical_position",
            "spin",
            "throttle_factor",
            "roll_factor",
            "pitch_factor",
            "yaw_force_factor",
            "yaw_drag_factor",
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in out_rows:
            writer.writerow({k: (f"{v:.6f}" if isinstance(v, float) else v) for k, v in row.items()})

    print(OUTPUT.resolve())


if __name__ == "__main__":
    main()
