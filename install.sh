#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $EUID -ne 0 ]]; then echo "Bitte mit sudo starten: sudo ./install.sh"; exit 1; fi
if [[ ! -r /etc/os-release ]]; then echo "Nicht unterstütztes System"; exit 1; fi
. /etc/os-release
if [[ "${ID:-}" != "debian" && "${ID:-}" != "raspbian" ]]; then echo "Hinweis: getestet für Raspberry Pi OS / Debian."; fi

APP_USER="${SUDO_USER:-pi}"
if ! id "$APP_USER" >/dev/null 2>&1; then echo "Benutzer $APP_USER existiert nicht"; exit 1; fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "[1/6] Pakete installieren"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y ffmpeg python3 python3-venv v4l-utils alsa-utils rsync avahi-daemon

echo "[2/6] Dateien kopieren"
mkdir -p /opt/pistreamer /etc/pistreamer
rsync -a --delete --exclude '.git' --exclude '.venv' "$SCRIPT_DIR/" /opt/pistreamer/
chown -R "$APP_USER:$APP_USER" /opt/pistreamer

echo "[3/6] Python-Umgebung erstellen"
sudo -u "$APP_USER" python3 -m venv /opt/pistreamer/.venv
sudo -u "$APP_USER" /opt/pistreamer/.venv/bin/pip install --upgrade pip
sudo -u "$APP_USER" /opt/pistreamer/.venv/bin/pip install -r /opt/pistreamer/requirements.txt

echo "[4/6] Konfiguration anlegen"
if [[ ! -f /etc/pistreamer/config.yaml ]]; then
  cp /opt/pistreamer/config/config.example.yaml /etc/pistreamer/config.yaml
  chmod 600 /etc/pistreamer/config.yaml
fi
chown root:"$APP_USER" /etc/pistreamer/config.yaml
usermod -aG video,audio "$APP_USER"

echo "[5/6] systemd installieren"
sed "s/__USER__/$APP_USER/g" /opt/pistreamer/systemd/pistreamer.service > /etc/systemd/system/pistreamer.service
systemctl daemon-reload
systemctl enable --now avahi-daemon pistreamer.service

echo "[6/6] Fertig"
IP=$(hostname -I | awk '{print $1}')
echo "Webinterface: http://pistreamer.local:8080 oder http://${IP:-PI-IP}:8080"
echo "Login: admin / change-me"
echo "WICHTIG: Passwort und YouTube-Key direkt im Webinterface ändern."
