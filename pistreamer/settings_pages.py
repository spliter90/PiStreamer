from __future__ import annotations

from pathlib import Path

from flask import redirect, render_template, request, url_for

from .app import app, auth_required, config, manager
from .config import save_config
from .profiles import STREAM_PROFILES, apply_profile


def _form_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(request.form.get(name, default))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


def _save(message: str):
    save_config(config)
    manager.config = config
    return redirect(url_for("settings_section", section=request.view_args["section"], saved=message))


@app.get("/settings-menu")
@auth_required
def settings_menu():
    return render_template("settings_menu.html")


@app.route("/settings/<section>", methods=["GET", "POST"])
@auth_required
def settings_section(section: str):
    allowed = {"target", "devices", "mobile", "recording", "appearance", "system"}
    if section not in allowed:
        return redirect(url_for("settings_menu"))

    error = None
    if request.method == "POST":
        stream = config["stream"]
        try:
            if section == "target":
                platform = request.form.get("platform", "youtube").lower()
                stream["platform"] = platform if platform in {"youtube", "twitch", "custom"} else "youtube"
                custom_url = request.form.get("custom_url", "").strip()
                if custom_url and not custom_url.lower().startswith(("rtmp://", "rtmps://")):
                    raise ValueError("Die Serveradresse muss mit rtmp:// oder rtmps:// beginnen.")
                stream["custom_url"] = custom_url
                submitted_key = request.form.get("stream_key", "").strip()
                if submitted_key:
                    stream["stream_key"] = submitted_key
                return _save("Streaming-Ziel gespeichert")

            if section == "devices":
                stream["video_device"] = request.form.get("video_device", "/dev/video0").strip()
                stream["audio_device"] = request.form.get("audio_device", "default").strip()
                stream["width"] = _form_int("width", 1280, 320, 3840)
                stream["height"] = _form_int("height", 720, 240, 2160)
                stream["fps"] = _form_int("fps", 30, 10, 60)
                stream["quality_profile"] = "custom"
                return _save("Geräte und Bildformat gespeichert")

            if section == "mobile":
                stream["auto_quality"] = request.form.get("auto_quality") == "on"
                profile = request.form.get("quality_profile", "mobile_standard")
                if profile == "custom":
                    stream["quality_profile"] = "custom"
                    stream["video_bitrate"] = request.form.get("video_bitrate", "1800k").strip()
                    stream["maxrate"] = request.form.get("maxrate", "2200k").strip()
                    stream["buffer_size"] = request.form.get("buffer_size", "4400k").strip()
                elif not apply_profile(stream, profile):
                    raise ValueError("Unbekanntes Qualitätsprofil.")
                stream["reconnect_enabled"] = request.form.get("reconnect_enabled") == "on"
                stream["reconnect_delay"] = _form_int("reconnect_delay", 3, 1, 60)
                return _save("Qualitäts- und Netzwerkeinstellungen gespeichert")

            if section == "recording":
                rec = config["recording"]
                rec["enabled"] = request.form.get("enabled") == "on"
                rec["path"] = request.form.get("path", "/opt/pistreamer/data/recordings").strip()
                rec["segment_seconds"] = _form_int("segment_seconds", 60, 10, 3600)
                rec["max_storage_gb"] = _form_int("max_storage_gb", 20, 1, 1000)
                rec["delete_oldest"] = request.form.get("delete_oldest") == "on"
                Path(rec["path"]).mkdir(parents=True, exist_ok=True)
                return _save("Aufnahme-Einstellungen gespeichert")

            if section == "appearance":
                overlay = config["overlay"]
                pause = config["pause_screen"]
                overlay["logo_enabled"] = request.form.get("logo_enabled") == "on"
                overlay["logo_path"] = request.form.get("logo_path", "").strip()
                overlay["logo_position"] = request.form.get("logo_position", "top_right")
                overlay["logo_width_percent"] = _form_int("logo_width_percent", 20, 5, 50)
                overlay["text_enabled"] = request.form.get("text_enabled") == "on"
                overlay["text"] = request.form.get("overlay_text", "").strip()
                overlay["text_position"] = request.form.get("text_position", "bottom_left")
                overlay["text_size"] = _form_int("text_size", 32, 12, 96)
                pause["image_path"] = request.form.get("pause_image_path", "").strip()
                return _save("Darstellung gespeichert")

            if section == "system":
                stream["autostart"] = request.form.get("autostart") == "on"
                password = request.form.get("password", "").strip()
                if password:
                    config["web"]["password"] = password
                return _save("System-Einstellungen gespeichert")
        except (OSError, ValueError) as exc:
            error = str(exc)

    return render_template(
        "settings_section.html",
        section=section,
        config=config,
        profiles=STREAM_PROFILES,
        message=request.args.get("saved"),
        error=error,
    )
