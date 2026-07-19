#!/usr/bin/env bash
set -Eeuo pipefail

REPO_URL="https://github.com/spliter90/PiStreamer.git"
INSTALL_DIR="/opt/pistreamer"
CONFIG_DIR="/etc/pistreamer"
RUNTIME_DIR="/run/pistreamer"
STATUS_FILE="$RUNTIME_DIR/update-status.json"
REQUEST_FILE="$RUNTIME_DIR/update.request"
BACKUP_DIR="/var/backups/pistreamer"
TMP_DIR=""
LOG_LINES=()

json_status() {
  local state="$1" message="$2"
  python3 - "$STATUS_FILE" "$state" "$message" "${LOG_LINES[@]:-}" <<'PY'
import json, os, sys, time
path, state, message, *lines = sys.argv[1:]
tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8") as fh:
    json.dump({"state": state, "message": message, "updated_at": int(time.time()), "log": lines[-40:]}, fh, ensure_ascii=False)
os.chmod(tmp, 0o664)
os.replace(tmp, path)
PY
}

step() {
  LOG_LINES+=("$1")
  json_status running "$1"
}

fail() {
  LOG_LINES+=("Fehler: $1")
  json_status error "$1"
  exit 1
}

cleanup() {
  rm -rf "${TMP_DIR:-}"
  rm -f "$REQUEST_FILE"
}
trap cleanup EXIT
trap 'fail "Update in Zeile $LINENO fehlgeschlagen."' ERR

mkdir -p "$RUNTIME_DIR" "$BACKUP_DIR"
chmod 2775 "$RUNTIME_DIR"
json_status queued "Update wird vorbereitet."

APP_USER="$(stat -c '%U' "$INSTALL_DIR" 2>/dev/null || true)"
APP_GROUP="$(stat -c '%G' "$INSTALL_DIR" 2>/dev/null || true)"
[[ -n "$APP_USER" && "$APP_USER" != "UNKNOWN" ]] || APP_USER="$(getent passwd 1000 | cut -d: -f1)"
[[ -n "$APP_GROUP" && "$APP_GROUP" != "UNKNOWN" ]] || APP_GROUP="$(id -gn "$APP_USER")"

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
step "Konfiguration sichern"
tar -czf "$BACKUP_DIR/config-$TIMESTAMP.tar.gz" -C / etc/pistreamer
find "$BACKUP_DIR" -type f -name 'config-*.tar.gz' -printf '%T@ %p\n' | sort -nr | awk 'NR>10 {print $2}' | xargs -r rm -f

step "Neueste Version herunterladen"
TMP_DIR="$(mktemp -d)"
git clone --depth 1 "$REPO_URL" "$TMP_DIR/source"

step "Programmdateien installieren"
rsync -a --delete \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude 'data/' \
  "$TMP_DIR/source/" "$INSTALL_DIR/"
chown -R "$APP_USER:$APP_GROUP" "$INSTALL_DIR"

step "Python-Abhängigkeiten aktualisieren"
sudo -u "$APP_USER" "$INSTALL_DIR/.venv/bin/python" -m pip install -r "$INSTALL_DIR/requirements.txt"

step "Systemd-Konfiguration aktualisieren"
install -m 0644 "$INSTALL_DIR/systemd/pistreamer-update.service" /etc/systemd/system/pistreamer-update.service
install -m 0644 "$INSTALL_DIR/systemd/pistreamer-update.path" /etc/systemd/system/pistreamer-update.path
systemctl daemon-reload
systemctl enable --now pistreamer-update.path >/dev/null

step "PiStreamer neu starten"
json_status success "Update erfolgreich. PiStreamer wird neu gestartet."
systemctl restart pistreamer.service
