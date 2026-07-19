from __future__ import annotations

import os
from pathlib import Path
import yaml

DEFAULT_CONFIG = {
    "web": {"host": "0.0.0.0", "port": 8080, "username": "admin", "password": "change-me"},
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
        "audio_bitrate": "128k",
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
}

CONFIG_PATH = Path(os.environ.get("PISTREAMER_CONFIG", "/etc/pistreamer/config.yaml"))


def load_config() -> dict:
    data = {section: values.copy() if isinstance(values, dict) else values for section, values in DEFAULT_CONFIG.items()}
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open("r", encoding="utf-8") as fh:
            loaded = yaml.safe_load(fh) or {}
        for section, values in loaded.items():
            if isinstance(values, dict) and isinstance(data.get(section), dict):
                data[section] = {**data[section], **values}
            else:
                data[section] = values

    stream = data.setdefault("stream", {})
    if stream.get("platform") not in {"youtube", "twitch", "custom"}:
        stream["platform"] = "youtube"
    return data


def save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(config, fh, sort_keys=False, allow_unicode=True)
    os.chmod(tmp, 0o660)
    tmp.replace(CONFIG_PATH)
