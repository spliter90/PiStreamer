from __future__ import annotations

from pathlib import Path

from flask import redirect, render_template, request, url_for

from .app import app, auth_required, config, manager
from .config import save_config
from .profiles import STREAM_PROFILES, apply_profile


def _defaults() -> None:
    stream = config.setdefault("stream", {})
    stream.setdefault("maxrate", stream.get("video_bitrate", "2500k"))
    stream.setdefault("buffer_size", "5000k")
    stream.setdefault("mobile_mode", False)
    stream.setdefault("quality_profile", "mobile_standard")
    stream.setdefault("auto_quality", False)
    stream.setdefault("reconnect_enabled", True)
    stream.setdefault("reconnect_delay", 3)
    config.setdefault("recording", {
        "enabled": False,
        "path": "/opt/pistreamer/data/recordings",
        "segment_seconds": 60,
        "max_storage_gb": 20,
        "delete_oldest": True,
    })


def _save(message: str):
    save_config(config)
    manager.config = config
    return redirect(url_for("settings_section", section=request.view_args["section"], saved=message))


@app.get("/settings-menu")
@auth_required
def settings_menu():
    _defaults()
    return render_template("settings_menu.html")


@app.route("/settings/<section>", methods=["GET", "POST"])
@auth_required
def settings_section(section: str):
    _defaults()
    allowed = {"target", "devices", "mobile", "recording", "appearance", "system"}
    if section not in allowed:
        return redirect(url_for("settings_menu"))

    if request.method == "POST":
        stream = config["stream"]
        if section == "target":
            platform = request.form.get("platform", "youtube").lower()
            stream["platform"] = platform if platform in {"youtube", "twitch", "custom"} else "youtube"
            stream["custom_url"] = request.form.get("custom_url", "").strip()
            submitted_key = request.form.get("stream_key", "").strip()
            if submitted_key:
                stream["stream_key"] = submitted_key
            return _save("Streaming-Ziel gespeichert")

        if section == "devices":
            stream["video_device"] = request.form.get("video_device", "/dev/video0").strip()
            stream["audio_device"] = request.form.get("audio_device", "default").strip()
            stream["width"] = max(320, min(3840, int(request.form.get("width", 1280))))
            stream["height"] = max(240, min(2160, int(request.form.get("height", 720))))
            stream["fps"] = max(10, min(60, int(request.form.get("fps", 30))))
            stream["quality_profile"] = "custom"
            return _save("Geräte und Bildformat gespeichert")

        if section == "mobile":
            stream["mobile_mode"] = request.form.get("mobile_mode") == "on"
            stream["auto_quality"] = request.form.get("auto_quality") == "on"
            profile = request.form.get("quality_profile", "mobile_standard")
            if profile == "custom":
                stream["quality_profile"] = "custom"
                stream["video_bitrate"] = request.form.get("video_bitrate", "1800k").strip()
                stream["maxrate"] = request.form.get("maxrate", "2200k").strip()
                stream["buffer_size"] = request.form.get("buffer_size", "4400k").strip()
            else:
                apply_profile(stream, profile)
            stream["reconnect_enabled"] = request.form.get("reconnect_enabled") == "on"
            stream["reconnect_delay"] = max(1, min(60, int(request.form.get("reconnect_delay", 3))))
            return _save("Qualitäts- und Netzwerkeinstellungen gespeichert")

        if section == "recording":
            rec = config["recording"]
            rec["enabled"] = request.form.get("enabled") == "on"
            rec["path"] = request.form.get("path", "/opt/pistreamer/data/recordings").strip()
            rec["segment_seconds"] = max(10, min(3600, int(request.form.get("segment_seconds", 60))))
            rec["max_storage_gb"] = max(1, min(1000, int(request.form.get("max_storage_gb", 20))))
            rec["delete_oldest"] = request.form.get("delete_oldest") == "on"
            Path(rec["path"]).mkdir(parents=True, exist_ok=True)
            return _save("Aufnahme-Einstellungen gespeichert")

        if section == "appearance":
            overlay = config.setdefault("overlay", {})
            pause = config.setdefault("pause_screen", {})
            overlay["logo_enabled"] = request.form.get("logo_enabled") == "on"
            overlay["logo_path"] = request.form.get("logo_path", "").strip()
            overlay["logo_position"] = request.form.get("logo_position", "top_right")
            overlay["logo_width_percent"] = max(5, min(50, int(request.form.get("logo_width_percent", 20))))
            overlay["text_enabled"] = request.form.get("text_enabled") == "on"
            overlay["text"] = request.form.get("overlay_text", "").strip()
            overlay["text_position"] = request.form.get("text_position", "bottom_left")
            overlay["text_size"] = max(12, min(96, int(request.form.get("text_size", 32))))
            pause["image_path"] = request.form.get("pause_image_path", "").strip()
            return _save("Darstellung gespeichert")

        if section == "system":
            stream["autostart"] = request.form.get("autostart") == "on"
            password = request.form.get("password", "").strip()
            if password:
                config["web"]["password"] = password
            return _save("System-Einstellungen gespeichert")

    return render_template("settings_section.html", section=section, config=config, profiles=STREAM_PROFILES, message=request.args.get("saved"))
