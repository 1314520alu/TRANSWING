import math


def v_add(a, b):
    return tuple(a[i] + b[i] for i in range(3))


def v_sub(a, b):
    return tuple(a[i] - b[i] for i in range(3))


def v_mul(a, s):
    return tuple(a[i] * s for i in range(3))


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


def rotate_about_axis(point, axis_point, axis_dir, angle_deg):
    """Rodrigues rotation around a fixed 3D axis."""
    k = unit(axis_dir)
    p = v_sub(point, axis_point)
    t = math.radians(angle_deg)
    return v_add(
        axis_point,
        v_add(
            v_add(v_mul(p, math.cos(t)), v_mul(cross(k, p), math.sin(t))),
            v_mul(k, dot(k, p) * (1.0 - math.cos(t))),
        ),
    )


# Body frame: X forward, Y right, Z down. Units: meters.
LEFT_AXIS_POINT = (0.196609, -0.346877, -0.148467)
LEFT_AXIS_DIR = unit((0.489150, 0.562537, -0.666547))
RIGHT_AXIS_POINT = (0.196609, 0.346877, -0.148467)
RIGHT_AXIS_DIR = unit((-0.489150, 0.562537, 0.666547))

# theta=0: unfolded/fixed-wing state from annotated image.
MOTORS_UNFOLDED = {
    "M1_left_front": (0.525, -0.320, -0.045),
    "M2_left_rear": (0.520, -0.980, -0.060),
    "M3_right_front": (0.525, 0.320, -0.045),
    "M4_right_rear": (0.520, 0.980, -0.060),
}

# theta=90: folded/VTOL state from annotated image.
MOTORS_FOLDED = {
    "M1_left_front": (0.155, -0.490, -0.460),
    "M2_left_rear": (-0.480, -0.460, -0.355),
    "M3_right_front": (0.155, 0.490, -0.460),
    "M4_right_rear": (-0.480, 0.460, -0.355),
}

LEFT_ANGLE_90_DEG = 122.851
RIGHT_ANGLE_90_DEG = 122.851


def smoothstep(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)


def motor_pose_axis(theta_deg):
    """Return motor centers using a best-fit equivalent fixed-axis model."""
    frac = theta_deg / 90.0
    left_angle = LEFT_ANGLE_90_DEG * frac
    right_angle = RIGHT_ANGLE_90_DEG * frac
    out = {}
    for name, p in MOTORS_UNFOLDED.items():
        if name.startswith("M1") or name.startswith("M2"):
            out[name] = rotate_about_axis(p, LEFT_AXIS_POINT, LEFT_AXIS_DIR, left_angle)
        else:
            out[name] = rotate_about_axis(p, RIGHT_AXIS_POINT, RIGHT_AXIS_DIR, right_angle)
    return out


def motor_pose_endpoint(theta_deg):
    """Return motor centers using endpoint interpolation.

    This is the robust table model for control allocation when the exact
    mechanical path is not yet confirmed from CAD.
    """
    s = smoothstep(theta_deg / 90.0)
    out = {}
    for name, p0 in MOTORS_UNFOLDED.items():
        p1 = MOTORS_FOLDED[name]
        out[name] = tuple(p0[i] * (1.0 - s) + p1[i] * s for i in range(3))
    return out


def print_table():
    print("endpoint_interpolation_table")
    print("theta_deg,motor,x_m,y_m,z_m")
    for theta in (0, 15, 30, 45, 60, 75, 90):
        poses = motor_pose_endpoint(theta)
        for name in sorted(poses):
            p = poses[name]
            print(f"{theta},{name},{p[0]:.6f},{p[1]:.6f},{p[2]:.6f}")


def print_endpoint_error():
    print("fixed_axis_model_endpoint_error_at_theta_90")
    poses = motor_pose_axis(90)
    for name, p in sorted(poses.items()):
        target = MOTORS_FOLDED[name]
        err = v_sub(p, target)
        print(
            f"{name}: pred=({p[0]:.6f},{p[1]:.6f},{p[2]:.6f}) "
            f"target=({target[0]:.6f},{target[1]:.6f},{target[2]:.6f}) "
            f"err_norm={norm(err):.6f}"
        )


if __name__ == "__main__":
    print_endpoint_error()
    print()
    print_table()
