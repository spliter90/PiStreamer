from __future__ import annotations

import copy
import os
from pathlib import Path

import yaml

DEFAULT_CONFIG = {
    "web": {
        "host": "0.0.0.0",
        "port": 8080,
        "username": "admin",
        "password": "change-me",
    },
    "stream": {
        "platform": "youtube",
        "youtube_url": "rtmp://a.rtmp.youtube.com/live2",
        "twitch_url": "rtmp://live.twitch.tv/app",
        "custom_url": "",
        "stream_key": "",
        "video_device": "/dev/video0",
        "audio_device": "default",
        "width": 1280,
        "height": 720,
        "fps": 30,
        "video_bitrate": "2500k",
        "maxrate": "3000k",
        "buffer_size": "6000k",
        "audio_bitrate": "128k",
        "quality_profile": "wifi_standard",
        "auto_quality": False,
        "reconnect_enabled": True,
        "reconnect_delay": 3,
        "autostart": False,
    },
    "overlay": {
        "logo_enabled": False,
        "logo_path": "/opt/pistreamer/data/logo.png",
        "logo_position": "top_right",
        "logo_width_percent": 20,
        "text_enabled": False,
        "text": "PiStreamer Live",
        "text_position": "bottom_left",
        "text_size": 32,
    },
    "pause_screen": {
        "image_path": "/opt/pistreamer/data/pause.png",
    },
    "recording": {
        "enabled": False,
        "path": "/opt/pistreamer/data/recordings",
        "segment_seconds": 60,
        "max_storage_gb": 20,
        "delete_oldest": True,
    },
    "system": {
        "timezone": "Europe/Berlin",
    },
}

CONFIG_PATH = Path(os.environ.get("PISTREAMER_CONFIG", "/etc/pistreamer/config.yaml"))


def _merge_dict(base: dict, loaded: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in loaded.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def load_config() -> dict:
    loaded: dict = {}
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open("r", encoding="utf-8") as fh:
            parsed = yaml.safe_load(fh) or {}
        if not isinstance(parsed, dict):
            raise ValueError("Die PiStreamer-Konfiguration muss ein YAML-Objekt sein.")
        loaded = parsed

    data = _merge_dict(DEFAULT_CONFIG, loaded)
    stream = data["stream"]
    if stream.get("platform") not in {"youtube", "twitch", "custom"}:
        stream["platform"] = "youtube"
    return data


def save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_suffix(CONFIG_PATH.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(config, fh, sort_keys=False, allow_unicode=True)
        fh.flush()
        os.fsync(fh.fileno())
    os.chmod(tmp, 0o660)
    tmp.replace(CONFIG_PATH)
