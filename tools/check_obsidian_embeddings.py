#!/usr/bin/env python3
"""Thin wrapper — delegates to Obsidian Vault _tools/check_embeddings.py."""
import os
import runpy
import sys

VAULT_TOOLS = os.path.join(
    os.environ.get("OBSIDIAN_VAULT", r"C:\Users\alu\Documents\Obsidian Vault"),
    "_tools",
    "check_embeddings.py",
)
if not os.path.isfile(VAULT_TOOLS):
    print(f"Vault tool not found: {VAULT_TOOLS}", file=sys.stderr)
    sys.exit(1)
runpy.run_path(VAULT_TOOLS, run_name="__main__")
