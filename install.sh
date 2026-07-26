#!/usr/bin/env bash
set -Eeuo pipefail

REPO_URL="https://github.com/spliter90/PiStreamer.git"
BASE_DIR="/opt/pistreamer"
RELEASES_DIR="$BASE_DIR/releases"
DATA_DIR="$BASE_DIR/data"
CURRENT_LINK="$BASE_DIR/current"
CONFIG_DIR="/etc/pistreamer"
CONFIG_FILE="$CONFIG_DIR/config.yaml"
SERVICE_FILE="/etc/systemd/system/pistreamer.service"
UPDATE_SERVICE_FILE="/etc/systemd/system/pistreamer-update.service"
UPDATE_PATH_FILE="/etc/systemd/system/pistreamer-update.path"
UPDATE_EXECUTABLE="/usr/local/libexec/pistreamer-update"
RUNTIME_DIR="/run/pistreamer"
INSTALL_LOG="/var/log/pistreamer-install.log"
MODE="install"
TMP_DIR=""
NEW_RELEASE=""
PREVIOUS_LINK=""

log() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
ok() { printf '\033[1;32m✓ %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33mHinweis: %s\033[0m\n' "$*"; }
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

retry() {
  local attempts="$1" delay="$2"
  shift 2
  local attempt
  for ((attempt = 1; attempt <= attempts; attempt++)); do
    if "$@"; then
      return 0
    fi
    if (( attempt < attempts )); then
      warn "Versuch $attempt/$attempts fehlgeschlagen; neuer Versuch in ${delay}s."
      sleep "$delay"
    fi
  done
  return 1
}

wait_for_apt() {
  local timeout=180 waited=0
  local locks=(
    /var/lib/dpkg/lock-frontend
    /var/lib/dpkg/lock
    /var/cache/apt/archives/lock
    /var/lib/apt/lists/lock
  )

  while command -v fuser >/dev/null 2>&1 && fuser "${locks[@]}" >/dev/null 2>&1; do
    (( waited == 0 )) && warn "Paketverwaltung ist belegt; warte maximal ${timeout}s."
    (( waited >= timeout )) && fail "Paketverwaltung blieb länger als ${timeout}s gesperrt."
    sleep 3
    waited=$((waited + 3))
  done
  dpkg --configure -a || fail "Eine unterbrochene Paketinstallation konnte nicht repariert werden."
}

valid_version() {
  [[ "$1" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]]
}

activate_release() {
  local release_name="$1"
  local new_link="$BASE_DIR/.current.new"
  rm -f "$new_link"
  ln -s "releases/$release_name" "$new_link"
  mv -Tf "$new_link" "$CURRENT_LINK"
}

rollback_release() {
  if [[ -n "$PREVIOUS_LINK" ]]; then
    warn "Dienststart fehlgeschlagen; vorherige Version wird wieder aktiviert."
    local rollback_link="$BASE_DIR/.current.rollback"
    rm -f "$rollback_link"
    ln -s "$PREVIOUS_LINK" "$rollback_link"
    mv -Tf "$rollback_link" "$CURRENT_LINK"
    systemctl daemon-reload
    systemctl restart pistreamer.service || true
  fi
}

prune_releases() {
  local keep=3 count=0 path
  while IFS= read -r path; do
    count=$((count + 1))
    if (( count > keep )); then
      rm -rf -- "$path"
    fi
  done < <(find "$RELEASES_DIR" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' | sort -nr | cut -d' ' -f2-)
}

case "${1:-}" in
  "") ;;
  --update|--upgrade) MODE="update" ;;
  --help|-h) usage; exit 0 ;;
  *) usage; fail "Unbekannte Option: $1" ;;
esac

[[ $EUID -eq 0 ]] || fail "Bitte mit sudo starten: sudo ./install.sh"
install -d -m 0755 "$(dirname "$INSTALL_LOG")"
touch "$INSTALL_LOG"
chmod 0644 "$INSTALL_LOG"
exec > >(tee -a "$INSTALL_LOG") 2>&1
printf '\n===== PiStreamer %s: %s =====\n' "$MODE" "$(date --iso-8601=seconds)"

[[ -r /etc/os-release ]] || fail "/etc/os-release fehlt; unterstützt werden Raspberry Pi OS und Debian."
. /etc/os-release
if [[ "${ID:-}" != "debian" && "${ID:-}" != "raspbian" ]]; then
  warn "Dieses Skript wurde für Raspberry Pi OS und Debian entwickelt (erkannt: ${PRETTY_NAME:-unbekannt})."
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
wait_for_apt
retry 3 5 apt-get update || fail "apt-get update ist nach drei Versuchen fehlgeschlagen."
retry 3 5 apt-get install -y \
  ca-certificates curl git rsync ffmpeg python3 python3-venv \
  v4l-utils alsa-utils avahi-daemon network-manager psmisc \
  || fail "Erforderliche Systempakete konnten nicht installiert werden."
ok "Systempakete sind vorhanden"

for group in video audio; do
  if ! getent group "$group" >/dev/null; then
    groupadd --system "$group"
  fi
  usermod -aG "$group" "$APP_USER"
done

if [[ "$MODE" == "update" ]]; then
  log "Saubere aktuelle PiStreamer-Version herunterladen"
  TMP_DIR="$(mktemp -d)"
  retry 3 5 git clone --depth 1 "$REPO_URL" "$TMP_DIR/PiStreamer" \
    || fail "Repository konnte nicht heruntergeladen werden."
  SOURCE_DIR="$TMP_DIR/PiStreamer"
elif [[ -f "$SCRIPT_DIR/run.py" && -f "$SCRIPT_DIR/requirements.txt" ]]; then
  SOURCE_DIR="$SCRIPT_DIR"
else
  log "Neueste PiStreamer-Version herunterladen"
  TMP_DIR="$(mktemp -d)"
  retry 3 5 git clone --depth 1 "$REPO_URL" "$TMP_DIR/PiStreamer" \
    || fail "Repository konnte nicht heruntergeladen werden."
  SOURCE_DIR="$TMP_DIR/PiStreamer"
fi

for required in run.py requirements.txt VERSION config/config.example.yaml \
  systemd/pistreamer.service systemd/pistreamer-update.service \
  systemd/pistreamer-update.path scripts/pistreamer-update.sh; do
  [[ -f "$SOURCE_DIR/$required" ]] || fail "Ungültige Quelldateien: $required fehlt."
done

VERSION="$(tr -d '[:space:]' < "$SOURCE_DIR/VERSION")"
valid_version "$VERSION" || fail "Ungültige Versionsnummer in VERSION: $VERSION"
RELEASE_NAME="${VERSION}-$(date +%Y%m%d%H%M%S)"
NEW_RELEASE="$RELEASES_DIR/$RELEASE_NAME"
PREVIOUS_LINK="$(readlink "$CURRENT_LINK" 2>/dev/null || true)"

log "Release $VERSION installieren"
install -d -m 0755 -o root -g root "$BASE_DIR" "$RELEASES_DIR"
install -d -m 0750 -o "$APP_USER" -g "$APP_GROUP" "$DATA_DIR"
install -d -m 0750 -o "$APP_USER" -g "$APP_GROUP" "$DATA_DIR/logs" "$DATA_DIR/recordings"
install -d -m 0755 -o root -g root "$NEW_RELEASE"
rsync -a --delete \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude 'data/' \
  "$SOURCE_DIR/" "$NEW_RELEASE/"
chown -R root:root "$NEW_RELEASE"
chmod -R go-w "$NEW_RELEASE"
ok "Programmdateien sind unveränderbar im Release-Verzeichnis installiert"

log "Python-Umgebung einrichten"
python3 -m venv "$NEW_RELEASE/.venv" || fail "Python-Umgebung konnte nicht erstellt werden."
retry 3 5 "$NEW_RELEASE/.venv/bin/python" -m pip install --upgrade pip \
  || fail "pip konnte nicht aktualisiert werden."
retry 3 5 "$NEW_RELEASE/.venv/bin/python" -m pip install -r "$NEW_RELEASE/requirements.txt" \
  || fail "Python-Abhängigkeiten konnten nicht installiert werden."
"$NEW_RELEASE/.venv/bin/python" -m compileall -q "$NEW_RELEASE/pistreamer" "$NEW_RELEASE/run.py" \
  || fail "Python-Quellcode enthält Syntaxfehler."
chown -R root:root "$NEW_RELEASE/.venv"
chmod -R go-w "$NEW_RELEASE/.venv"
ok "Python-Abhängigkeiten installiert und geprüft"

log "Konfiguration einrichten"
install -d -m 2770 -o root -g "$APP_GROUP" "$CONFIG_DIR"
if [[ ! -f "$CONFIG_FILE" ]]; then
  install -m 0660 -o root -g "$APP_GROUP" "$NEW_RELEASE/config/config.example.yaml" "$CONFIG_FILE"
  ok "Neue Konfiguration angelegt"
else
  chown root:"$APP_GROUP" "$CONFIG_FILE"
  chmod 0660 "$CONFIG_FILE"
  ok "Vorhandene Konfiguration beibehalten"
fi

log "Root-Update-Dienst sicher installieren"
install -d -m 0755 -o root -g root "$(dirname "$UPDATE_EXECUTABLE")"
install -m 0755 -o root -g root "$NEW_RELEASE/scripts/pistreamer-update.sh" "$UPDATE_EXECUTABLE"
install -m 0644 -o root -g root "$NEW_RELEASE/systemd/pistreamer-update.service" "$UPDATE_SERVICE_FILE"
install -m 0644 -o root -g root "$NEW_RELEASE/systemd/pistreamer-update.path" "$UPDATE_PATH_FILE"
install -d -m 2775 -o root -g "$APP_GROUP" "$RUNTIME_DIR"

log "systemd-Dienste einrichten"
sed \
  -e "s/__USER__/$APP_USER/g" \
  -e "s/__GROUP__/$APP_GROUP/g" \
  "$NEW_RELEASE/systemd/pistreamer.service" > "$SERVICE_FILE"
chown root:root "$SERVICE_FILE"
chmod 0644 "$SERVICE_FILE"
systemd-analyze verify "$SERVICE_FILE" "$UPDATE_SERVICE_FILE" "$UPDATE_PATH_FILE" >/dev/null \
  || fail "Eine erzeugte systemd-Datei ist ungültig."

activate_release "$RELEASE_NAME"
systemctl daemon-reload
systemctl enable avahi-daemon pistreamer.service pistreamer-update.path >/dev/null
systemctl enable NetworkManager >/dev/null 2>&1 || true
systemctl restart avahi-daemon
if ! systemctl is-active --quiet NetworkManager; then
  systemctl start NetworkManager || warn "NetworkManager konnte nicht gestartet werden."
fi
systemctl restart pistreamer-update.path
if ! systemctl restart pistreamer.service || ! systemctl is-active --quiet pistreamer.service; then
  systemctl status pistreamer.service --no-pager --full || true
  journalctl -u pistreamer.service -n 100 --no-pager || true
  rollback_release
  fail "PiStreamer konnte nicht gestartet werden. Installationsprotokoll: $INSTALL_LOG"
fi

# Entfernt nur veraltete Programmdateien aus Installationen vor dem Release-Modell.
for legacy in run.py requirements.txt VERSION pistreamer config systemd scripts docs tests .github; do
  [[ -e "$BASE_DIR/$legacy" || -L "$BASE_DIR/$legacy" ]] && rm -rf -- "$BASE_DIR/$legacy"
done
prune_releases
ok "PiStreamer läuft mit Release $VERSION"

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
printf 'Installationslog: %s\n' "$INSTALL_LOG"
