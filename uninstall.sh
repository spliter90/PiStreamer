#!/usr/bin/env bash
set -Eeuo pipefail
[[ $EUID -eq 0 ]] || { echo "Bitte mit sudo starten"; exit 1; }
systemctl disable --now pistreamer.service 2>/dev/null || true
rm -f /etc/systemd/system/pistreamer.service
systemctl daemon-reload
rm -rf /opt/pistreamer
echo "PiStreamer entfernt. Konfiguration bleibt in /etc/pistreamer erhalten."
