#!/usr/bin/env python3
"""Read a short MAVLink snapshot for Transwing SITL debugging."""

import math
import sys
import time

from pymavlink import mavutil


ENDPOINTS = (
    "tcp:127.0.0.1:5760",
    "udp:127.0.0.1:14550",
)


def connect():
    endpoints = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    endpoints = tuple(endpoints) or ENDPOINTS
    last_error = None
    for endpoint in endpoints:
        try:
            print(f"TRY {endpoint}")
            mav = mavutil.mavlink_connection(
                endpoint,
                source_system=255,
                autoreconnect=False,
                timeout=2,
            )
            heartbeat = mav.wait_heartbeat(timeout=3)
            print(
                "HEARTBEAT",
                endpoint,
                "sys",
                mav.target_system,
                "comp",
                mav.target_component,
                "type",
                heartbeat.type,
            )
            return mav
        except Exception as exc:  # noqa: BLE001 - diagnostic script
            last_error = exc
            print(f"FAIL {endpoint}: {exc!r}")
    raise SystemExit(f"No MAVLink connection: {last_error!r}")


def option_value(name, default=None):
    prefix = f"{name}="
    for arg in sys.argv[1:]:
        if arg.startswith(prefix):
            return arg.removeprefix(prefix)
    return default


def has_option(name):
    return name in sys.argv[1:]


def main():
    mav = connect()
    target_component = mav.target_component or 1
    pre_wait = float(option_value("--pre-wait", "0"))
    if pre_wait > 0:
        print("PRE_WAIT", pre_wait)
        time.sleep(pre_wait)

    mode_name = option_value("--mode", None)
    if mode_name:
        mapping = mav.mode_mapping()
        if mode_name not in mapping:
            print("MODE_MAP", sorted(mapping))
            raise SystemExit(f"Unknown mode: {mode_name}")
        mav.set_mode_apm(mapping[mode_name])
        print("SET_MODE", mode_name, mapping[mode_name])

    settle_after_mode = float(option_value("--settle-after-mode", "0"))
    if settle_after_mode > 0:
        print("SETTLE_AFTER_MODE", settle_after_mode)
        time.sleep(settle_after_mode)

    if has_option("--arm"):
        mav.mav.command_long_send(
            mav.target_system,
            target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            1,
            21196,
            0,
            0,
            0,
            0,
            0,
        )
        print("ARM_SENT force")

    throttle = option_value("--throttle", None)
    throttle_pwm = int(throttle) if throttle is not None else None

    mav.mav.request_data_stream_send(
        mav.target_system,
        target_component,
        mavutil.mavlink.MAV_DATA_STREAM_ALL,
        10,
        1,
    )

    for msg_id in (
        mavutil.mavlink.MAVLINK_MSG_ID_ATTITUDE,
        mavutil.mavlink.MAVLINK_MSG_ID_SERVO_OUTPUT_RAW,
        mavutil.mavlink.MAVLINK_MSG_ID_SYS_STATUS,
        mavutil.mavlink.MAVLINK_MSG_ID_LOCAL_POSITION_NED,
        mavutil.mavlink.MAVLINK_MSG_ID_RC_CHANNELS,
    ):
        mav.mav.command_long_send(
            mav.target_system,
            target_component,
            mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
            0,
            msg_id,
            100000,
            0,
            0,
            0,
            0,
            0,
        )

    latest = {}
    text_messages = []
    command_acks = []
    start = time.time()
    while time.time() - start < 5:
        if throttle_pwm is not None:
            mav.mav.rc_channels_override_send(
                mav.target_system,
                target_component,
                65535,
                65535,
                throttle_pwm,
                65535,
                65535,
                65535,
                65535,
                65535,
            )
        msg = mav.recv_match(blocking=True, timeout=1)
        if msg is not None:
            msg_type = msg.get_type()
            latest[msg_type] = msg
            if msg_type == "STATUSTEXT":
                text_messages.append(msg.text)
            elif msg_type == "COMMAND_ACK":
                command_acks.append((msg.command, msg.result))

    if throttle_pwm is not None:
        print("RC3_OVERRIDE", throttle_pwm)

    if "HEARTBEAT" in latest:
        msg = latest["HEARTBEAT"]
        modes = mav.mode_mapping()
        mode_by_id = {value: key for key, value in modes.items()}
        print("HEARTBEAT_MODE", mode_by_id.get(msg.custom_mode, msg.custom_mode), "base", msg.base_mode)

    for command, result in command_acks[-8:]:
        print("COMMAND_ACK", command, result)

    for text in text_messages[-12:]:
        print("STATUSTEXT", text)

    if "ATTITUDE" in latest:
        msg = latest["ATTITUDE"]
        print(
            "ATTITUDE roll/pitch/yaw deg",
            round(math.degrees(msg.roll), 2),
            round(math.degrees(msg.pitch), 2),
            round(math.degrees(msg.yaw), 2),
        )

    if "SERVO_OUTPUT_RAW" in latest:
        msg = latest["SERVO_OUTPUT_RAW"]
        vals = [getattr(msg, f"servo{i}_raw", None) for i in range(1, 13)]
        print("SERVO1-12", vals)

    if "RC_CHANNELS" in latest:
        msg = latest["RC_CHANNELS"]
        vals = [getattr(msg, f"chan{i}_raw", None) for i in range(1, 9)]
        print("RC1-8", vals)

    if "SYS_STATUS" in latest:
        msg = latest["SYS_STATUS"]
        print(
            "SYS voltage/current/remain",
            msg.voltage_battery,
            msg.current_battery,
            msg.battery_remaining,
        )

    if "LOCAL_POSITION_NED" in latest:
        msg = latest["LOCAL_POSITION_NED"]
        print(
            "LOCAL NED x/y/z vx/vy/vz",
            round(msg.x, 2),
            round(msg.y, 2),
            round(msg.z, 2),
            round(msg.vx, 2),
            round(msg.vy, 2),
            round(msg.vz, 2),
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
