from __future__ import annotations

import socket
import time

import psutil
from flask import jsonify

from .app import api_auth_required, app, config, manager, temperature
from .network_monitor import NetworkMonitor

monitor = NetworkMonitor(manager)


def _stream_details() -> dict:
    stream = config.get("stream", {})
    process = manager.process
    return {
        "platform": stream.get("platform", "youtube"),
        "profile": stream.get("quality_profile", "custom"),
        "auto_quality": bool(stream.get("auto_quality", False)),
        "resolution": f"{stream.get('width', '–')}×{stream.get('height', '–')}",
        "fps": stream.get("fps"),
        "video_bitrate": stream.get("video_bitrate", "–"),
        "audio_bitrate": stream.get("audio_bitrate", "–"),
        "video_device": stream.get("video_device", "–"),
        "audio_device": stream.get("audio_device", "–"),
        "ffmpeg_pid": process.pid if process and process.poll() is None else None,
        "ffmpeg_speed": manager.ffmpeg_speed,
        "reconnects": manager.reconnects,
        "dropped_frames": manager.dropped_frames,
        "recent_failures": manager.recent_failures,
    }


@app.get("/api/network/status")
@api_auth_required
def network_status():
    return jsonify(monitor.snapshot())


@app.get("/api/dashboard")
@api_auth_required
def dashboard_status():
    network = monitor.snapshot()
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    boot_time = psutil.boot_time()
    return jsonify({
        "timestamp": int(time.time()),
        "system": {
            "hostname": socket.gethostname(),
            "cpu": psutil.cpu_percent(interval=0.1),
            "ram": memory.percent,
            "temperature": temperature(),
            "disk": disk.percent,
            "system_uptime": max(0, int(time.time() - boot_time)),
        },
        "stream": {
            "streaming": manager.is_running(),
            "paused": manager.paused,
            "uptime": manager.uptime(),
            **_stream_details(),
        },
        "network": network,
        "logs": list(manager.logs)[-120:],
    })
