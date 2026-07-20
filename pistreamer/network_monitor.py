from __future__ import annotations

import threading
import time
from collections import deque

import psutil


class NetworkMonitor:
    def __init__(self, manager):
        self.manager = manager
        self._history: deque[dict] = deque(maxlen=120)
        self._lock = threading.Lock()
        self._last_bytes = psutil.net_io_counters().bytes_sent
        self._last_time = time.monotonic()
        self._thread = threading.Thread(target=self._run, daemon=True, name="network-monitor")
        self._thread.start()

    def _run(self) -> None:
        while True:
            now = time.monotonic()
            counters = psutil.net_io_counters()
            elapsed = max(0.001, now - self._last_time)
            upload_mbps = max(0.0, (counters.bytes_sent - self._last_bytes) * 8 / elapsed / 1_000_000)
            self._last_bytes = counters.bytes_sent
            self._last_time = now

            item = {
                "time": int(time.time()),
                "upload_mbps": round(upload_mbps, 2),
                "streaming": self.manager.is_running(),
                "reconnects": self.manager.reconnects,
                "dropped_frames": self.manager.dropped_frames,
                "speed": self.manager.ffmpeg_speed,
            }
            with self._lock:
                self._history.append(item)
            time.sleep(5)

    def snapshot(self) -> dict:
        with self._lock:
            history = list(self._history)
        latest = history[-1] if history else {
            "time": int(time.time()),
            "upload_mbps": 0.0,
            "streaming": False,
            "reconnects": 0,
            "dropped_frames": 0,
            "speed": None,
        }
        health = "offline"
        message = "Stream ist nicht aktiv"
        if latest["streaming"]:
            speed = latest.get("speed")
            if self.manager.recent_failures >= 2 or (speed is not None and speed < 0.85):
                health, message = "critical", "Verbindung oder Encoder instabil"
            elif self.manager.recent_failures or (speed is not None and speed < 0.97):
                health, message = "warning", "Stream läuft mit geringer Reserve"
            else:
                health, message = "good", "Stream läuft stabil"
        return {
            **latest,
            "health": health,
            "message": message,
            "profile": self.manager.config.get("stream", {}).get("quality_profile", "custom"),
            "auto_quality": bool(self.manager.config.get("stream", {}).get("auto_quality", False)),
            "history": history[-60:],
        }
