from __future__ import annotations

import hmac
import os
import socket
import subprocess
from functools import wraps

import psutil
from flask import Flask, jsonify, redirect, render_template, request, session, url_for

from .config import load_config, save_config
from .streamer import StreamManager

config = load_config()
app = Flask(__name__)
app.secret_key = os.environ.get("PISTREAMER_SECRET", os.urandom(32))
manager = StreamManager(config)


def auth_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapped


def api_auth_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("authenticated"):
            return jsonify({"error": "unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapped


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        web = config["web"]
        ok_user = hmac.compare_digest(request.form.get("username", ""), str(web["username"]))
        ok_pass = hmac.compare_digest(request.form.get("password", ""), str(web["password"]))
        if ok_user and ok_pass:
            session["authenticated"] = True
            return redirect(url_for("index"))
        error = "Anmeldung fehlgeschlagen"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@auth_required
def index():
    return render_template("index.html")


def temperature() -> float | None:
    try:
        raw = open("/sys/class/thermal/thermal_zone0/temp", encoding="utf-8").read().strip()
        return round(int(raw) / 1000, 1)
    except (OSError, ValueError):
        return None


@app.get("/api/status")
@api_auth_required
def status():
    return jsonify({
        "streaming": manager.is_running(),
        "paused": manager.paused,
        "uptime": manager.uptime(),
        "cpu": psutil.cpu_percent(interval=0.1),
        "ram": psutil.virtual_memory().percent,
        "temperature": temperature(),
        "hostname": socket.gethostname(),
        "platform": config["stream"].get("platform", "youtube"),
        "video_device": config["stream"]["video_device"],
        "audio_device": config["stream"]["audio_device"],
    })


@app.post("/api/start")
@api_auth_required
def start():
    try:
        manager.paused = False
        manager.start()
        return jsonify({"ok": True})
    except Exception as exc:
        manager.logs.append(f"Startfehler: {exc}")
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.post("/api/stop")
@api_auth_required
def stop():
    manager.stop()
    return jsonify({"ok": True})


@app.post("/api/restart")
@api_auth_required
def restart():
    try:
        manager.restart()
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.post("/api/pause")
@api_auth_required
def pause():
    try:
        manager.pause()
        return jsonify({"ok": True})
    except Exception as exc:
        manager.logs.append(f"Pausenfehler: {exc}")
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.post("/api/resume")
@api_auth_required
def resume():
    try:
        manager.resume()
        return jsonify({"ok": True})
    except Exception as exc:
        manager.logs.append(f"Fortsetzen fehlgeschlagen: {exc}")
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.get("/api/logs")
@api_auth_required
def logs():
    return jsonify({"lines": list(manager.logs)})


@app.get("/api/devices")
@api_auth_required
def devices():
    videos = sorted(str(p) for p in __import__("pathlib").Path("/dev").glob("video*"))
    try:
        audio = subprocess.run(["arecord", "-L"], capture_output=True, text=True, timeout=5).stdout.splitlines()
        audio = [line.strip() for line in audio if line and not line.startswith(" ")]
    except Exception:
        audio = []
    return jsonify({"video": videos, "audio": audio})


@app.route("/settings", methods=["GET", "POST"])
@auth_required
def settings():
    global config
    message = None
    if request.method == "POST":
        s = config["stream"]
        w = config["web"]
        overlay = config.setdefault("overlay", {})
        pause_screen = config.setdefault("pause_screen", {})

        platform = request.form.get("platform", "youtube").strip().lower()
        if platform not in {"youtube", "twitch", "custom"}:
            platform = "youtube"
        custom_url = request.form.get("custom_url", "").strip()
        if custom_url and not custom_url.lower().startswith(("rtmp://", "rtmps://")):
            return render_template(
                "settings.html",
                config=config,
                message=None,
                error="Die benutzerdefinierte Serveradresse muss mit rtmp:// oder rtmps:// beginnen.",
            ), 400

        s["platform"] = platform
        s["custom_url"] = custom_url
        s["stream_key"] = request.form.get("stream_key", "").strip()
        s["video_device"] = request.form.get("video_device", "/dev/video0").strip()
        s["audio_device"] = request.form.get("audio_device", "default").strip()
        s["fps"] = int(request.form.get("fps", 30))
        s["video_bitrate"] = request.form.get("video_bitrate", "2500k").strip()
        s["autostart"] = request.form.get("autostart") == "on"

        overlay["logo_enabled"] = request.form.get("logo_enabled") == "on"
        overlay["logo_path"] = request.form.get("logo_path", "").strip()
        overlay["logo_position"] = request.form.get("logo_position", "top_right")
        overlay["logo_width_percent"] = max(5, min(50, int(request.form.get("logo_width_percent", 20))))
        overlay["text_enabled"] = request.form.get("text_enabled") == "on"
        overlay["text"] = request.form.get("overlay_text", "").strip()
        overlay["text_position"] = request.form.get("text_position", "bottom_left")
        overlay["text_size"] = max(12, min(96, int(request.form.get("text_size", 32))))
        pause_screen["image_path"] = request.form.get("pause_image_path", "").strip()

        new_password = request.form.get("password", "").strip()
        if new_password:
            w["password"] = new_password
        save_config(config)
        manager.config = config
        message = "Einstellungen gespeichert"

    masked = {**config, "stream": {**config["stream"], "stream_key": config["stream"].get("stream_key", "")}}
    return render_template("settings.html", config=masked, message=message, error=None)


if config["stream"].get("autostart"):
    try:
        manager.start()
    except Exception as exc:
        manager.logs.append(f"Autostart fehlgeschlagen: {exc}")
