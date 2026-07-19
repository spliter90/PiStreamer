#!/usr/bin/env bash
set -Eeuo pipefail

REPO_URL="https://github.com/spliter90/PiStreamer.git"
INSTALL_DIR="/opt/pistreamer"
CONFIG_DIR="/etc/pistreamer"
CONFIG_FILE="$CONFIG_DIR/config.yaml"
SERVICE_FILE="/etc/systemd/system/pistreamer.service"
MODE="install"

log() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
ok() { printf '\033[1;32m✓ %s\033[0m\n' "$*"; }
fail() { printf '\033[1;31mFehler: %s\033[0m\n' "$*" >&2; exit 1; }

usage() {
  cat <<USAGE
PiStreamer Installer

Verwendung:
  sudo ./install.sh             Installation oder erneute Einrichtung
  sudo ./install.sh --update    Neueste Version installieren und Dienst neu starten
  sudo ./install.sh --help      Hilfe anzeigen
USAGE
}

case "${1:-}" in
  "") ;;
  --update|--upgrade) MODE="update" ;;
  --help|-h) usage; exit 0 ;;
  *) usage; fail "Unbekannte Option: $1" ;;
esac

[[ $EUID -eq 0 ]] || fail "Bitte mit sudo starten: sudo ./install.sh"
[[ -r /etc/os-release ]] || fail "/etc/os-release fehlt; unterstützt werden Raspberry Pi OS und Debian."
. /etc/os-release
if [[ "${ID:-}" != "debian" && "${ID:-}" != "raspbian" ]]; then
  printf 'Hinweis: Dieses Skript wurde für Raspberry Pi OS und Debian entwickelt (erkannt: %s).\n' "${PRETTY_NAME:-unbekannt}"
fi

APP_USER="${PISTREAMER_USER:-${SUDO_USER:-}}"
if [[ -z "$APP_USER" || "$APP_USER" == "root" ]]; then
  APP_USER="$(getent passwd 1000 | cut -d: -f1 || true)"
fi
[[ -n "$APP_USER" ]] || fail "Kein normaler Benutzer gefunden. Setze PISTREAMER_USER, z. B. sudo PISTREAMER_USER=chris ./install.sh"
id "$APP_USER" >/dev/null 2>&1 || fail "Benutzer '$APP_USER' existiert nicht."
APP_GROUP="$(id -gn "$APP_USER")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log "Systempakete installieren"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  ca-certificates curl git rsync ffmpeg python3 python3-venv \
  v4l-utils alsa-utils avahi-daemon
ok "Systempakete sind vorhanden"

if [[ "$MODE" == "update" && -d "$SCRIPT_DIR/.git" ]]; then
  log "Lokalen PiStreamer-Klon aktualisieren"
  sudo -u "$APP_USER" git -C "$SCRIPT_DIR" pull --ff-only
  SOURCE_DIR="$SCRIPT_DIR"
elif [[ "$MODE" == "install" && -f "$SCRIPT_DIR/run.py" && -f "$SCRIPT_DIR/requirements.txt" ]]; then
  SOURCE_DIR="$SCRIPT_DIR"
else
  log "Neueste PiStreamer-Version herunterladen"
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "${TMP_DIR:-}"' EXIT
  git clone --depth 1 "$REPO_URL" "$TMP_DIR/PiStreamer"
  SOURCE_DIR="$TMP_DIR/PiStreamer"
fi

log "Programm nach $INSTALL_DIR installieren"
mkdir -p "$INSTALL_DIR" "$INSTALL_DIR/data" "$CONFIG_DIR"
if [[ "$SOURCE_DIR" != "$INSTALL_DIR" ]]; then
  rsync -a --delete \
    --exclude '.git/' \
    --exclude '.venv/' \
    --exclude 'data/' \
    "$SOURCE_DIR/" "$INSTALL_DIR/"
fi
chown -R "$APP_USER:$APP_GROUP" "$INSTALL_DIR"
ok "Programmdateien installiert; $INSTALL_DIR/data bleibt erhalten"

log "Python-Umgebung einrichten"
if [[ ! -x "$INSTALL_DIR/.venv/bin/python" ]]; then
  sudo -u "$APP_USER" python3 -m venv "$INSTALL_DIR/.venv"
fi
sudo -u "$APP_USER" "$INSTALL_DIR/.venv/bin/python" -m pip install --upgrade pip
sudo -u "$APP_USER" "$INSTALL_DIR/.venv/bin/python" -m pip install -r "$INSTALL_DIR/requirements.txt"
ok "Python-Abhängigkeiten installiert"

log "Konfiguration einrichten"
if [[ ! -f "$CONFIG_FILE" ]]; then
  install -m 0640 -o root -g "$APP_GROUP" "$INSTALL_DIR/config/config.example.yaml" "$CONFIG_FILE"
  ok "Neue Konfiguration angelegt"
else
  chown root:"$APP_GROUP" "$CONFIG_FILE"
  chmod 0640 "$CONFIG_FILE"
  ok "Vorhandene Konfiguration beibehalten"
fi
usermod -aG video,audio "$APP_USER"

log "systemd-Dienst einrichten"
sed \
  -e "s/__USER__/$APP_USER/g" \
  -e "s/__GROUP__/$APP_GROUP/g" \
  "$INSTALL_DIR/systemd/pistreamer.service" > "$SERVICE_FILE"
systemctl daemon-reload
systemctl enable avahi-daemon pistreamer.service >/dev/null
systemctl restart avahi-daemon
systemctl restart pistreamer.service

if ! systemctl is-active --quiet pistreamer.service; then
  journalctl -u pistreamer.service -n 30 --no-pager || true
  fail "PiStreamer konnte nicht gestartet werden."
fi
ok "PiStreamer läuft"

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
printf '\n========================================\n'
printf ' PiStreamer wurde erfolgreich %s.\n' "$([[ "$MODE" == "update" ]] && echo aktualisiert || echo installiert)"
printf '========================================\n\n'
printf 'Webinterface: http://pistreamer.local:8080\n'
printf 'Alternativ:   http://%s:8080\n' "${IP:-PI-IP}"
printf 'Login:        admin / change-me\n\n'
printf 'Wichtig: Passwort und YouTube-Stream-Key direkt ändern.\n'
printf 'Status: sudo systemctl status pistreamer\n'
printf 'Logs:   sudo journalctl -u pistreamer -f\n'