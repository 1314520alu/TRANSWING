#!/usr/bin/env python3
"""Measure SERVO11 / fold slew rate from DataFlash BIN logs."""
import statistics
import sys
from pathlib import Path

from pymavlink import mavutil

PWM_FW, PWM_Q = 2000, 1000


def pwm_to_theta(pwm: float) -> float:
    ratio = max(0.0, min(1.0, (pwm - PWM_FW) / (PWM_Q - PWM_FW)))
    return ratio * 90.0


def analyze(log: str) -> None:
    ml = mavutil.mavlink_connection(log)
    rcou, twng, parms = [], [], {}
    while True:
        m = ml.recv_match(blocking=False)
        if m is None:
            break
        t = m.get_type()
        if t == "RCOU":
            c11 = getattr(m, "C11", None)
            if c11 and c11 > 500:
                ts = m.TimeUS / 1e6
                rcou.append((ts, c11, pwm_to_theta(c11)))
        elif t == "TWNG":
            twng.append((m.TimeUS / 1e6, m.Targ, m.Est, m.Fold))
        elif t == "PARM" and m.Name in (
            "TW_RATE_UP", "TW_RATE_DN", "Q_TILT_RATE_UP", "Q_TILT_RATE_DN", "TW_MIX_MODE"
        ):
            parms[m.Name] = m.Value

    name = Path(log).name
    print(f"\n======== {name} ========")
    print(
        "Params:",
        {k: parms.get(k) for k in [
            "TW_RATE_UP", "TW_RATE_DN", "Q_TILT_RATE_UP", "Q_TILT_RATE_DN", "TW_MIX_MODE"
        ]},
    )

    seg_rates_deg, seg_rates_pwm = [], []
    i = 0
    while i < len(rcou) - 1:
        t0, p0, th0 = rcou[i]
        j = i + 1
        while j < len(rcou) and abs(rcou[j][1] - rcou[j - 1][1]) <= 15:
            j += 1
        if j - i >= 3:
            t1, p1, th1 = rcou[j - 1]
            dt = t1 - t0
            if dt > 0.05:
                dp = abs(p1 - p0)
                dth = abs(th1 - th0)
                if dp >= 20 and dth >= 0.5:
                    seg_rates_pwm.append(dp / dt)
                    seg_rates_deg.append(dth / dt)
        i = max(i + 1, j - 1)

    if seg_rates_deg:
        print(f"RCOU C11 sustained segments (n={len(seg_rates_deg)}):")
        print(
            f"  theta deg/s: min={min(seg_rates_deg):.1f} "
            f"med={statistics.median(seg_rates_deg):.1f} "
            f"max={max(seg_rates_deg):.1f} mean={statistics.mean(seg_rates_deg):.1f}"
        )
        print(
            f"  PWM u/s:     min={min(seg_rates_pwm):.0f} "
            f"med={statistics.median(seg_rates_pwm):.0f} max={max(seg_rates_pwm):.0f}"
        )

    steps = []
    for i in range(1, len(rcou)):
        dt = rcou[i][0] - rcou[i - 1][0]
        dth = abs(rcou[i][2] - rcou[i - 1][2])
        dp = abs(rcou[i][1] - rcou[i - 1][1])
        if dt < 0.15 and dth > 3:
            steps.append((rcou[i][0], dth, dp, dth / dt if dt > 0 else 0.0))
    print(f"RCOU instant jumps >3 deg in <150 ms: {len(steps)}")
    for ts, dth, dp, rate in steps[:10]:
        print(f"  {ts:7.1f}s jump {dth:5.1f} deg ({dp:4d} pwm) ~{rate:5.0f} deg/s")

    est_rates = []
    for i in range(1, len(twng)):
        dt = twng[i][0] - twng[i - 1][0]
        dth = abs(twng[i][2] - twng[i - 1][2])
        if dt > 0 and dth > 0.01:
            est_rates.append(dth / dt)
    if est_rates:
        print(
            f"TWNG Est deg/s: min={min(est_rates):.1f} "
            f"med={statistics.median(est_rates):.1f} max={max(est_rates):.1f}"
        )

    fold_rates = []
    for i in range(1, len(twng)):
        dt = twng[i][0] - twng[i - 1][0]
        dth = abs(pwm_to_theta(twng[i][3]) - pwm_to_theta(twng[i - 1][3]))
        if dt > 0 and dth > 0.01:
            fold_rates.append(dth / dt)
    if fold_rates:
        print(
            f"TWNG Fold deg/s: med={statistics.median(fold_rates):.1f} "
            f"max={max(fold_rates):.1f}"
        )

    # full 90->0 or 0->90 transitions
    for label, series in [("RCOU", rcou), ("TWNG Fold", [(t, f, pwm_to_theta(f)) for t, _, _, f in twng])]:
        if len(series) < 2:
            continue
        for direction in ("down", "up"):
            start = None
            for ts, pwm, th in series:
                if start is None:
                    if direction == "down" and th > 80:
                        start = (ts, th, pwm)
                    elif direction == "up" and th < 10:
                        start = (ts, th, pwm)
                    continue
                if direction == "down" and th < 5:
                    dt = ts - start[0]
                    dth = abs(th - start[1])
                    if dt > 1:
                        print(
                            f"{label} full fold {direction}: {start[0]:.1f}-{ts:.1f}s "
                            f"{start[1]:.0f}->{th:.0f} deg in {dt:.1f}s => {dth/dt:.2f} deg/s avg"
                        )
                    start = None
                elif direction == "up" and th > 85:
                    dt = ts - start[0]
                    dth = abs(th - start[1])
                    if dt > 1:
                        print(
                            f"{label} full unfold {direction}: {start[0]:.1f}-{ts:.1f}s "
                            f"{start[1]:.0f}->{th:.0f} deg in {dt:.1f}s => {dth/dt:.2f} deg/s avg"
                        )
                    start = None


def main() -> None:
    logs = sys.argv[1:] or [
        str(Path.home() / "ardupilot/ArduPlane/transwing_dynamic_mp/logs/00000028.BIN"),
        str(Path.home() / "ardupilot/ArduPlane/transwing_dynamic_mp/logs/00000027.BIN"),
    ]
    for log in logs:
        analyze(log)


if __name__ == "__main__":
    main()
