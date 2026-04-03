#!/usr/bin/env bash
set -euo pipefail

echo "== Host =="
hostname -f || true
echo
echo "== IP =="
ip addr || true
echo
echo "== Listening ports =="
ss -tulpn || true
echo
echo "== Running services =="
systemctl list-units --type=service --state=running || true
echo
echo "== Timers =="
systemctl list-timers --all || true
echo
echo "== Nginx config =="
if command -v nginx >/dev/null 2>&1; then
  nginx -T || true
else
  echo "nginx not installed"
fi
echo
echo "== Docker =="
if command -v docker >/dev/null 2>&1; then
  docker ps || true
else
  echo "docker not installed"
fi
