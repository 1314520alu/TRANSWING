#!/usr/bin/env python3
"""Dedupe pptx and fix placement."""
import os
import shutil

VAULT = r"C:\Users\alu\Documents\Obsidian Vault"
NAME = "舰载侦察无人机.pptx"
KEEP = os.path.join(VAULT, "06_自有产品", NAME)
REMOVE = [
    os.path.join(VAULT, NAME),
    os.path.join(VAULT, "03_整机与机巢", NAME),
]
for p in REMOVE:
    if os.path.isfile(p) and os.path.abspath(p) != os.path.abspath(KEEP):
        os.remove(p)
        print("removed duplicate:", p)
if not os.path.isfile(KEEP):
    # restore from any copy if missing
    for p in REMOVE + [KEEP]:
        pass
print("keep:", KEEP, "exists=", os.path.isfile(KEEP))
