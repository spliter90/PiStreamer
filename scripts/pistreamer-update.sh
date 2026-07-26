#!/usr/bin/env bash
set -Eeuo pipefail

REPO_URL="https://github.com/spliter90/PiStreamer.git"
BASE_DIR="/opt/pistreamer"
RELEASES_DIR="$BASE_DIR/releases"
CURRENT_LINK="$BASE_DIR/current"
DATA_DIR="$BASE_DIR/data"
CONFIG_DIR="/etc/pistreamer"
RUNTIME_DIR="/run/pistreamer"
STATUS_FILE="$RUNTIME_DIR/update-status.json"
REQUEST_FILE="$RUNTIME_DIR/update.request"
BACKUP_DIR="/var/backups/pistreamer"
UPDATE_EXECUTABLE="/usr/local/libexec/pistreamer-update"
TMP_DIR=""
PREVIOUS_LINK=""
NEW_RELEASE=""
UNIT_BACKUP_DIR=""
LOG_LINES=()

json_status() {
  local state="$1" message="$2"
  python3 - "$STATUS_FILE" "$state" "$message" "${LOG_LINES[@]:-}" <<'PY'
import json
import os
import sys
import time

path, state, message, *lines = sys.argv[1:]
os.makedirs(os.path.dirname(path), exist_ok=True)
tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8") as fh:
    json.dump(
        {"state": state, "message": message, "updated_at": int(time.time()), "log": lines[-60:]},
        fh,
        ensure_ascii=False,
    )
os.chmod(tmp, 0o664)
os.replace(tmp, path)
PY
}

step() {
  LOG_LINES+=("$1")
  json_status running "$1"
}

activate_release() {
  local release_name="$1"
  local new_link="$BASE_DIR/.current.new"
  rm -f "$new_link"
  ln -s "releases/$release_name" "$new_link"
  mv -Tf "$new_link" "$CURRENT_LINK"
}

restore_previous_release() {
  [[ -n "$PREVIOUS_LINK" ]] || return 0
  LOG_LINES+=("Rollback auf vorherige Version")
  local rollback_link="$BASE_DIR/.current.rollback"
  rm -f "$rollback_link"
  ln -s "$PREVIOUS_LINK" "$rollback_link"
  mv -Tf "$rollback_link" "$CURRENT_LINK"
  if [[ -n "$UNIT_BACKUP_DIR" && -d "$UNIT_BACKUP_DIR" ]]; then
    for unit in pistreamer.service pistreamer-update.service pistreamer-update.path; do
      if [[ -f "$UNIT_BACKUP_DIR/$unit" ]]; then
        install -m 0644 -o root -g root "$UNIT_BACKUP_DIR/$unit" "/etc/systemd/system/$unit"
      fi
    done
  fi
  systemctl daemon-reload || true
  systemctl restart pistreamer.service || true
}

fail() {
  trap - ERR
  local message="$1"
  LOG_LINES+=("Fehler: $message")
  restore_previous_release
  json_status error "$message"
  exit 1
}

cleanup() {
  rm -rf "${TMP_DIR:-}"
  rm -f "$REQUEST_FILE"
}
trap cleanup EXIT
trap 'fail "Update in Zeile $LINENO fehlgeschlagen: $BASH_COMMAND"' ERR

retry() {
  local attempts="$1" delay="$2"
  shift 2
  local attempt
  for ((attempt = 1; attempt <= attempts; attempt++)); do
    if "$@"; then
      return 0
    fi
    if (( attempt < attempts )); then
      LOG_LINES+=("Versuch $attempt/$attempts fehlgeschlagen")
      json_status running "Temporärer Fehler; neuer Versuch in ${delay}s."
      sleep "$delay"
    fi
  done
  return 1
}

valid_version() {
  [[ "$1" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]]
}

prune_releases() {
  local current_real keep=3 count=0 path
  current_real="$(readlink -f "$CURRENT_LINK")"
  while IFS= read -r path; do
    [[ "$(readlink -f "$path")" == "$current_real" ]] && continue
    count=$((count + 1))
    if (( count >= keep )); then
      rm -rf -- "$path"
    fi
  done < <(find "$RELEASES_DIR" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' | sort -nr | cut -d' ' -f2-)
}

[[ $EUID -eq 0 ]] || exit 1
mkdir -p "$RUNTIME_DIR" "$BACKUP_DIR" "$RELEASES_DIR"
chmod 2775 "$RUNTIME_DIR"
json_status queued "Update wird vorbereitet."

[[ -L "$CURRENT_LINK" ]] || fail "Aktive Release-Verknüpfung fehlt. Bitte install.sh erneut ausführen."
PREVIOUS_LINK="$(readlink "$CURRENT_LINK")"
APP_USER="$(systemctl show pistreamer.service --property=User --value)"
APP_GROUP="$(systemctl show pistreamer.service --property=Group --value)"
[[ -n "$APP_USER" && -n "$APP_GROUP" ]] || fail "Dienstbenutzer oder Dienstgruppe konnte nicht ermittelt werden."

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
step "Konfiguration sichern"
tar -czf "$BACKUP_DIR/config-$TIMESTAMP.tar.gz" -C / etc/pistreamer
find "$BACKUP_DIR" -type f -name 'config-*.tar.gz' -printf '%T@ %p\n' | sort -nr | awk 'NR>10 {print $2}' | xargs -r rm -f

step "Neueste Version herunterladen"
TMP_DIR="$(mktemp -d)"
UNIT_BACKUP_DIR="$TMP_DIR/unit-backup"
mkdir -p "$UNIT_BACKUP_DIR"
for unit in pistreamer.service pistreamer-update.service pistreamer-update.path; do
  [[ -f "/etc/systemd/system/$unit" ]] && cp -a "/etc/systemd/system/$unit" "$UNIT_BACKUP_DIR/$unit"
done
retry 3 5 git clone --depth 1 "$REPO_URL" "$TMP_DIR/source" \
  || fail "Repository konnte nicht heruntergeladen werden."
for required in run.py requirements.txt VERSION config/config.example.yaml \
  systemd/pistreamer.service systemd/pistreamer-update.service \
  systemd/pistreamer-update.path scripts/pistreamer-update.sh; do
  [[ -f "$TMP_DIR/source/$required" ]] || fail "Quelldatei fehlt: $required"
done

VERSION="$(tr -d '[:space:]' < "$TMP_DIR/source/VERSION")"
valid_version "$VERSION" || fail "Ungültige Versionsnummer: $VERSION"
RELEASE_NAME="${VERSION}-${TIMESTAMP}"
NEW_RELEASE="$RELEASES_DIR/$RELEASE_NAME"

step "Release $VERSION vorbereiten"
install -d -m 0755 -o root -g root "$NEW_RELEASE"
rsync -a --delete \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude 'data/' \
  "$TMP_DIR/source/" "$NEW_RELEASE/"
chown -R root:root "$NEW_RELEASE"
chmod -R go-w "$NEW_RELEASE"

step "Isolierte Python-Umgebung installieren"
python3 -m venv "$NEW_RELEASE/.venv" || fail "Python-Umgebung konnte nicht erstellt werden."
retry 3 5 "$NEW_RELEASE/.venv/bin/python" -m pip install --upgrade pip \
  || fail "pip konnte nicht aktualisiert werden."
retry 3 5 "$NEW_RELEASE/.venv/bin/python" -m pip install -r "$NEW_RELEASE/requirements.txt" \
  || fail "Python-Abhängigkeiten konnten nicht installiert werden."
"$NEW_RELEASE/.venv/bin/python" -m compileall -q "$NEW_RELEASE/pistreamer" "$NEW_RELEASE/run.py" \
  || fail "Python-Prüfung ist fehlgeschlagen."
chown -R root:root "$NEW_RELEASE/.venv"
chmod -R go-w "$NEW_RELEASE/.venv"

step "systemd-Konfiguration prüfen"
sed \
  -e "s/__USER__/$APP_USER/g" \
  -e "s/__GROUP__/$APP_GROUP/g" \
  "$NEW_RELEASE/systemd/pistreamer.service" > "$TMP_DIR/pistreamer.service"
systemd-analyze verify \
  "$TMP_DIR/pistreamer.service" \
  "$NEW_RELEASE/systemd/pistreamer-update.service" \
  "$NEW_RELEASE/systemd/pistreamer-update.path" >/dev/null \
  || fail "Neue systemd-Konfiguration ist ungültig."

step "Neue Version atomar aktivieren"
activate_release "$RELEASE_NAME"
install -m 0644 -o root -g root "$TMP_DIR/pistreamer.service" /etc/systemd/system/pistreamer.service
install -m 0644 -o root -g root "$NEW_RELEASE/systemd/pistreamer-update.service" /etc/systemd/system/pistreamer-update.service
install -m 0644 -o root -g root "$NEW_RELEASE/systemd/pistreamer-update.path" /etc/systemd/system/pistreamer-update.path
systemctl daemon-reload

step "PiStreamer mit Version $VERSION neu starten"
if ! systemctl restart pistreamer.service || ! systemctl is-active --quiet pistreamer.service; then
  systemctl status pistreamer.service --no-pager --full || true
  journalctl -u pistreamer.service -n 100 --no-pager || true
  fail "Neue Version konnte nicht gestartet werden."
fi

# Der aktuell laufende Updater wird erst nach einem erfolgreichen Dienststart ersetzt.
install -m 0755 -o root -g root "$NEW_RELEASE/scripts/pistreamer-update.sh" "$UPDATE_EXECUTABLE"
systemctl enable --now pistreamer-update.path >/dev/null
prune_releases
LOG_LINES+=("Update auf $VERSION erfolgreich")
json_status success "Update auf Version $VERSION erfolgreich."
