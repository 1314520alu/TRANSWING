#!/bin/bash
set -euo pipefail

ARCHIVE="/mnt/c/Users/alu/Downloads/maxkb-v2.10.2-lts-x86_64-offline-installer.tar.gz"
EXTRACT_ROOT="$HOME/maxkb-offline"
INSTALL_DIR="$EXTRACT_ROOT/maxkb-v2.10.2-lts-x86_64-offline-installer"

if [ ! -f "$ARCHIVE" ]; then
  echo "ERROR: installer not found: $ARCHIVE"
  exit 1
fi

if [ ! -f "$INSTALL_DIR/install.sh" ]; then
  echo "==> Extracting MaxKB offline package (1.3GB, please wait)..."
  mkdir -p "$EXTRACT_ROOT"
  tar -xzf "$ARCHIVE" -C "$EXTRACT_ROOT"
fi

echo "==> Starting MaxKB install (requires sudo)..."
cd "$INSTALL_DIR"
sudo bash install.sh

echo ""
echo "==> Install script finished. Checking service..."
if command -v mkctl >/dev/null 2>&1; then
  sudo mkctl status || true
fi

echo ""
echo "Open in Windows browser: http://localhost:8080"
echo "Login: admin / MaxKB@123.."
