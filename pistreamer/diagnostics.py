from __future__ import annotations

import logging
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import jsonify, render_template, request

from .app import app, api_auth_required, auth_required, config
from .logging_setup import DEFAULT_TIMEZONE, apply_timezone, configure_logging, read_log_lines


def configured_timezone() -> str:
    return str(config.setdefault("system", {}).setdefault("timezone", DEFAULT_TIMEZONE))


logger = configure_logging(configured_timezone())

# Route Flask/Werkzeug messages into the persistent PiStreamer log.
app.logger.handlers.clear()
for handler in logger.handlers:
    app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)
app.logger.propagate = False
logging.getLogger("werkzeug").setLevel(logging.WARNING)


@app.before_request
def log_request_start() -> None:
    if request.path.startswith("/static/") or request.path in {"/api/status", "/api/logs", "/api/server-logs"}:
        return
    app.logger.info("HTTP %s %s von %s", request.method, request.path, request.remote_addr or "unbekannt")


@app.errorhandler(Exception)
def log_unhandled_exception(exc: Exception):
    app.logger.exception("Unbehandelter Serverfehler bei %s %s", request.method, request.path)
    return jsonify({"error": "Interner Serverfehler"}), 500


def clock_info() -> dict:
    timezone = configured_timezone()
    try:
        now = datetime.now(ZoneInfo(timezone))
    except ZoneInfoNotFoundError:
        timezone = apply_timezone(DEFAULT_TIMEZONE)
        now = datetime.now(ZoneInfo(timezone))

    result = {
        "timezone": timezone,
        "local_time": now.isoformat(timespec="seconds"),
        "utc_offset": now.strftime("%z"),
        "ntp_synchronized": None,
        "system_timezone": None,
    }
    try:
        output = subprocess.run(
            ["timedatectl", "show", "--property=Timezone", "--property=NTPSynchronized", "--value"],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        ).stdout.splitlines()
        if output:
            result["system_timezone"] = output[0].strip() or None
        if len(output) > 1:
            result["ntp_synchronized"] = output[1].strip().lower() == "yes"
    except (OSError, subprocess.TimeoutExpired):
        pass
    return result


@app.get("/logs")
@auth_required
def log_center():
    return render_template("logs.html", clock=clock_info())


@app.get("/api/server-logs")
@api_auth_required
def server_logs_api():
    try:
        limit = int(request.args.get("limit", "300"))
    except ValueError:
        limit = 300
    return jsonify({"lines": read_log_lines(limit), "clock": clock_info()})


@app.get("/api/clock")
@api_auth_required
def clock_api():
    return jsonify(clock_info())
