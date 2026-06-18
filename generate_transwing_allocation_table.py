import csv
import math
from pathlib import Path


def dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def norm(a):
    return math.sqrt(dot(a, a))


def unit(a):
    n = norm(a)
    return tuple(x / n for x in a)


def smoothstep(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)


def interp(a, b, s):
    return tuple(a[i] * (1.0 - s) + b[i] * s for i in range(3))


# User-confirmed ArduPilot Quad X numbering and Motor Test mapping:
# Motor Test A -> M1 right/front, B -> M4 right/rear,
# C -> M2 left/rear, D -> M3 left/front.
MOTORS = [
    ("M1", "A", "right_front", "CCW", (0.525, 0.320, -0.045), (0.155, 0.490, -0.460)),
    ("M2", "C", "left_rear", "CCW", (0.520, -0.980, -0.060), (-0.480, -0.460, -0.355)),
    ("M3", "D", "left_front", "CW", (0.525, -0.320, -0.045), (0.155, -0.490, -0.460)),
    ("M4", "B", "right_rear", "CW", (0.520, 0.980, -0.060), (-0.480, 0.460, -0.355)),
]

# Body frame: X forward, Y right, Z down.
# Thrust vector is force direction on the vehicle.
THRUST_UNFOLDED = (1.0, 0.0, 0.0)
THRUST_FOLDED = (0.0, 0.0, -1.0)

# Yaw drag sign convention for this data table only:
# CCW is +1 and CW is -1. Verify final sign in ArduPilot motor test/logs.
YAW_SIGN = {
    "CCW": 1,
    "CW": -1,
}


def allocation_row(theta_deg, motor_name, test_letter, physical_position, spin, p0, p90):
    s = smoothstep(theta_deg / 90.0)
    r = interp(p0, p90, s)
    d = unit(interp(THRUST_UNFOLDED, THRUST_FOLDED, s))
    moment = cross(r, d)

    # Positive body moments: roll Mx, pitch My, yaw Mz.
    # In NED body frame, upward lift is negative Z force, so throttle_z is d.z.
    return {
        "theta_deg": theta_deg,
        "motor": motor_name,
        "test_letter": test_letter,
        "physical_position": physical_position,
        "spin": spin,
        "x_m": r[0],
        "y_m": r[1],
        "z_m": r[2],
        "dx": d[0],
        "dy": d[1],
        "dz": d[2],
        "vertical_factor_dz": d[2],
        "roll_moment_x": moment[0],
        "pitch_moment_y": moment[1],
        "yaw_moment_z_from_force": moment[2],
        "yaw_drag_sign": YAW_SIGN[spin],
    }


def main():
    out = Path("transwing_allocation_table.csv")
    fields = [
        "theta_deg",
        "motor",
        "test_letter",
        "physical_position",
        "spin",
        "x_m",
        "y_m",
        "z_m",
        "dx",
        "dy",
        "dz",
        "vertical_factor_dz",
        "roll_moment_x",
        "pitch_moment_y",
        "yaw_moment_z_from_force",
        "yaw_drag_sign",
    ]
    rows = []
    for theta in (0, 15, 30, 45, 60, 75, 90):
        for name, test_letter, physical_position, spin, p0, p90 in MOTORS:
            rows.append(allocation_row(theta, name, test_letter, physical_position, spin, p0, p90))

    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: (f"{v:.9f}" if isinstance(v, float) else v) for k, v in row.items()})

    print(out.resolve())


if __name__ == "__main__":
    main()
