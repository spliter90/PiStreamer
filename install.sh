#!/usr/bin/env bash
set -Eeuo pipefail

REPO_URL="https://github.com/spliter90/PiStreamer.git"
INSTALL_DIR="/opt/pistreamer"
CONFIG_DIR="/etc/pistreamer"
CONFIG_FILE="$CONFIG_DIR/config.yaml"
SERVICE_FILE="/etc/systemd/system/pistreamer.service"
UPDATE_SERVICE_FILE="/etc/systemd/system/pistreamer-update.service"
UPDATE_PATH_FILE="/etc/systemd/system/pistreamer-update.path"
RUNTIME_DIR="/run/pistreamer"
MODE="install"
TMP_DIR=""

log() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
ok() { printf '\033[1;32m✓ %s\033[0m\n' "$*"; }
fail() { printf '\033[1;31mFehler: %s\033[0m\n' "$*" >&2; exit 1; }
cleanup() { [[ -n "$TMP_DIR" ]] && rm -rf "$TMP_DIR"; }
trap cleanup EXIT
trap 'printf "\nFehler in Zeile %s: %s\n" "$LINENO" "$BASH_COMMAND" >&2' ERR

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

log "Systempakete prüfen"
export DEBIAN_FRONTEND=noninteractive
for attempt in 1 2 3; do
  if apt-get update; then
    break
  fi
  [[ $attempt -lt 3 ]] || fail "apt-get update ist nach drei Versuchen fehlgeschlagen."
  sleep 5
done
apt-get install -y \
  ca-certificates curl git rsync ffmpeg python3 python3-venv \
  v4l-utils alsa-utils avahi-daemon network-manager
ok "Systempakete sind vorhanden"

if [[ "$MODE" == "update" ]]; then
  log "Saubere aktuelle PiStreamer-Version herunterladen"
  TMP_DIR="$(mktemp -d)"
  git clone --depth 1 "$REPO_URL" "$TMP_DIR/PiStreamer"
  SOURCE_DIR="$TMP_DIR/PiStreamer"
elif [[ -f "$SCRIPT_DIR/run.py" && -f "$SCRIPT_DIR/requirements.txt" ]]; then
  SOURCE_DIR="$SCRIPT_DIR"
else
  log "Neueste PiStreamer-Version herunterladen"
  TMP_DIR="$(mktemp -d)"
  git clone --depth 1 "$REPO_URL" "$TMP_DIR/PiStreamer"
  SOURCE_DIR="$TMP_DIR/PiStreamer"
fi

[[ -f "$SOURCE_DIR/run.py" ]] || fail "Ungültige Quelldateien: run.py fehlt."
[[ -f "$SOURCE_DIR/requirements.txt" ]] || fail "Ungültige Quelldateien: requirements.txt fehlt."

log "Programm nach $INSTALL_DIR installieren"
mkdir -p "$INSTALL_DIR" "$INSTALL_DIR/data" "$CONFIG_DIR"
if [[ "$(readlink -f "$SOURCE_DIR")" != "$(readlink -f "$INSTALL_DIR")" ]]; then
  rsync -a --delete \
    --exclude '.git/' \
    --exclude '.venv/' \
    --exclude 'data/' \
    "$SOURCE_DIR/" "$INSTALL_DIR/"
fi
chown -R "$APP_USER:$APP_GROUP" "$INSTALL_DIR"
if [[ -f "$INSTALL_DIR/scripts/pistreamer-update.sh" ]]; then
  chmod 0755 "$INSTALL_DIR/scripts/pistreamer-update.sh"
fi
ok "Programmdateien installiert; $INSTALL_DIR/data bleibt erhalten"

log "Python-Umgebung einrichten"
if [[ ! -x "$INSTALL_DIR/.venv/bin/python" ]]; then
  runuser -u "$APP_USER" -- python3 -m venv "$INSTALL_DIR/.venv"
fi
runuser -u "$APP_USER" -- env HOME="$(getent passwd "$APP_USER" | cut -d: -f6)" \
  "$INSTALL_DIR/.venv/bin/python" -m pip install --upgrade pip
runuser -u "$APP_USER" -- env HOME="$(getent passwd "$APP_USER" | cut -d: -f6)" \
  "$INSTALL_DIR/.venv/bin/python" -m pip install -r "$INSTALL_DIR/requirements.txt"
ok "Python-Abhängigkeiten installiert"

log "Konfiguration einrichten"
chown root:"$APP_GROUP" "$CONFIG_DIR"
chmod 2770 "$CONFIG_DIR"
if [[ ! -f "$CONFIG_FILE" ]]; then
  install -m 0660 -o root -g "$APP_GROUP" "$INSTALL_DIR/config/config.example.yaml" "$CONFIG_FILE"
  ok "Neue Konfiguration angelegt"
else
  chown root:"$APP_GROUP" "$CONFIG_FILE"
  chmod 0660 "$CONFIG_FILE"
  ok "Vorhandene Konfiguration beibehalten"
fi
usermod -aG video,audio "$APP_USER"

log "Update-Center einrichten"
install -d -m 2775 -o root -g "$APP_GROUP" "$RUNTIME_DIR"
if [[ -f "$INSTALL_DIR/systemd/pistreamer-update.service" && -f "$INSTALL_DIR/systemd/pistreamer-update.path" ]]; then
  install -m 0644 "$INSTALL_DIR/systemd/pistreamer-update.service" "$UPDATE_SERVICE_FILE"
  install -m 0644 "$INSTALL_DIR/systemd/pistreamer-update.path" "$UPDATE_PATH_FILE"
  ok "Update-Dienst eingerichtet"
else
  printf 'Hinweis: Update-Center-Dateien fehlen; Update-Dienst wird übersprungen.\n'
fi

log "systemd-Dienste einrichten"
sed \
  -e "s/__USER__/$APP_USER/g" \
  -e "s/__GROUP__/$APP_GROUP/g" \
  "$INSTALL_DIR/systemd/pistreamer.service" > "$SERVICE_FILE"
systemctl daemon-reload
systemctl enable avahi-daemon pistreamer.service >/dev/null
systemctl enable NetworkManager >/dev/null 2>&1 || true
if [[ -f "$UPDATE_PATH_FILE" ]]; then
  systemctl enable pistreamer-update.path >/dev/null
fi
systemctl restart avahi-daemon
# NetworkManager wird absichtlich nicht neu gestartet: Ein Neustart kann eine
# laufende SSH- oder Web-Verbindung während der Installation unterbrechen.
if ! systemctl is-active --quiet NetworkManager; then
  systemctl start NetworkManager || printf 'Hinweis: NetworkManager konnte nicht gestartet werden.\n'
fi
if [[ -f "$UPDATE_PATH_FILE" ]]; then
  systemctl restart pistreamer-update.path
fi
systemctl restart pistreamer.service

if ! systemctl is-active --quiet pistreamer.service; then
  journalctl -u pistreamer.service -n 50 --no-pager || true
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
printf 'Wichtig: Passwort und Stream-Key direkt ändern.\n'
printf 'Status: sudo systemctl status pistreamer\n'
printf 'Logs:   sudo journalctl -u pistreamer -f\n'