#!/usr/bin/env python3
"""Shared MAVLink helpers for Transwing SITL tools."""

def param_name(msg):
    pid = msg.param_id
    if isinstance(pid, bytes):
        return pid.decode().rstrip("\x00")
    return str(pid).rstrip("\x00")


def status_text(msg):
    text = msg.text
    if isinstance(text, bytes):
        return text.decode(errors="replace")
    return str(text)
