from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from flask import jsonify, redirect, render_template, request, url_for

from .app import app, auth_required, api_auth_required

APP_DIR = Path(__file__).resolve().parent.parent
VERSION_FILE = APP_DIR / "VERSION"
RUNTIME_DIR = Path("/run/pistreamer")
REQUEST_FILE = RUNTIME_DIR / "update.request"
STATUS_FILE = RUNTIME_DIR / "update-status.json"
REMOTE_VERSION_URL = "https://raw.githubusercontent.com/spliter90/PiStreamer/main/VERSION"


def installed_version() -> str:
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip() or "unbekannt"
    except OSError:
        return "unbekannt"


def version_tuple(value: str) -> tuple[int, ...]:
    cleaned = value.strip().lstrip("v")
    try:
        return tuple(int(part) for part in cleaned.split("."))
    except ValueError:
        return (0,)


def latest_version() -> tuple[str | None, str | None]:
    request_obj = urllib.request.Request(
        REMOTE_VERSION_URL,
        headers={"User-Agent": "PiStreamer-Update-Check"},
    )
    try:
        with urllib.request.urlopen(request_obj, timeout=8) as response:
            return response.read().decode("utf-8").strip(), None
    except (OSError, urllib.error.URLError, UnicodeError) as exc:
        return None, str(exc)


def read_status() -> dict:
    try:
        data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def update_info(check_remote: bool = True) -> dict:
    current = installed_version()
    latest = None
    error = None
    if check_remote:
        latest, error = latest_version()
    return {
        "installed": current,
        "latest": latest,
        "update_available": bool(latest and version_tuple(latest) > version_tuple(current)),
        "check_error": error,
        "status": read_status(),
    }


@app.get("/settings/update")
@auth_required
def update_center():
    return render_template("update.html", info=update_info(), message=request.args.get("message"))


@app.get("/api/update/status")
@api_auth_required
def update_status_api():
    return jsonify(update_info(check_remote=request.args.get("remote") == "1"))


@app.post("/api/update/check")
@api_auth_required
def update_check_api():
    return jsonify(update_info(check_remote=True))


@app.post("/api/update/install")
@api_auth_required
def update_install_api():
    status = read_status()
    if status.get("state") in {"queued", "running"}:
        return jsonify({"ok": False, "error": "Ein Update läuft bereits."}), 409

    try:
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        request_data = {
            "requested_at": int(time.time()),
            "requested_by": "webinterface",
            "pid": os.getpid(),
        }
        temp = REQUEST_FILE.with_suffix(".tmp")
        temp.write_text(json.dumps(request_data), encoding="utf-8")
        os.chmod(temp, 0o660)
        temp.replace(REQUEST_FILE)
    except OSError as exc:
        return jsonify({"ok": False, "error": f"Update konnte nicht angefordert werden: {exc}"}), 500

    return jsonify({"ok": True, "message": "Update wurde gestartet."})


@app.get("/update")
@auth_required
def update_shortcut():
    return redirect(url_for("update_center"))
