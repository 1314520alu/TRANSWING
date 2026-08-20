#!/bin/bash
# Fix MaxKB Docker on WSL2 (iptables / nftables issue)
set -euo pipefail

echo "==> WSL Docker fix for MaxKB"
echo "    If this fails, use Docker Desktop instead (see FEISHU_GUIDE or README)."

sudo mkdir -p /etc/docker

# WSL2: bundled dockerd often fails on iptables/nftables
sudo tee /etc/docker/daemon.json >/dev/null <<'EOF'
{
  "iptables": false,
  "ip-masq": false
}
EOF

echo "==> Restarting Docker..."
sudo systemctl daemon-reload
sudo systemctl restart docker
sleep 5

if ! sudo docker info >/dev/null 2>&1; then
  echo ""
  echo "Docker still failed. Error log:"
  sudo journalctl -u docker --no-pager -n 30 || true
  echo ""
  echo "Try manual debug:  sudo /usr/bin/dockerd"
  echo ""
  echo "RECOMMENDED on Windows: install Docker Desktop, enable WSL integration,"
  echo "then run:  sudo mkctl reload"
  exit 1
fi

echo "==> Docker OK"
sudo mkctl reload
echo ""
echo "Open http://localhost:8080  (admin / MaxKB@123..)"
