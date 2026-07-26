#!/usr/bin/env bash
set -Eeuo pipefail
[[ $EUID -eq 0 ]] || { echo "Bitte mit sudo starten"; exit 1; }

systemctl disable --now pistreamer-update.path 2>/dev/null || true
systemctl stop pistreamer-update.service 2>/dev/null || true
systemctl disable --now pistreamer.service 2>/dev/null || true
rm -f \
  /etc/systemd/system/pistreamer.service \
  /etc/systemd/system/pistreamer-update.service \
  /etc/systemd/system/pistreamer-update.path \
  /usr/local/libexec/pistreamer-update
systemctl daemon-reload
systemctl reset-failed pistreamer.service pistreamer-update.service 2>/dev/null || true
rm -rf /opt/pistreamer /run/pistreamer

echo "PiStreamer wurde entfernt. Konfiguration in /etc/pistreamer und Sicherungen in /var/backups/pistreamer bleiben erhalten."
