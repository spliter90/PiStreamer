from __future__ import annotations

import subprocess
import threading
import time
from collections import deque
from pathlib import Path


class StreamManager:
    def __init__(self, config: dict):
        self.config = config
        self.process: subprocess.Popen[str] | None = None
        self.started_at: float | None = None
        self.logs: deque[str] = deque(maxlen=300)
        self._lock = threading.Lock()

    def _command(self) -> list[str]:
        s = self.config["stream"]
        if not s.get("stream_key"):
            raise ValueError("YouTube-Stream-Key fehlt")
        target = f"{s['youtube_url'].rstrip('/')}/{s['stream_key']}"
        return [
            "ffmpeg", "-hide_banner", "-loglevel", "info",
            "-f", "v4l2", "-framerate", str(s["fps"]),
            "-video_size", f"{s['width']}x{s['height']}",
            "-i", s["video_device"],
            "-f", "alsa", "-i", s["audio_device"],
            "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency",
            "-b:v", s["video_bitrate"], "-maxrate", s["video_bitrate"],
            "-bufsize", "5000k", "-pix_fmt", "yuv420p",
            "-g", str(int(s["fps"]) * 2), "-keyint_min", str(int(s["fps"]) * 2),
            "-c:a", "aac", "-b:a", s["audio_bitrate"], "-ar", "44100",
            "-f", "flv", target,
        ]

    def start(self) -> None:
        with self._lock:
            if self.is_running():
                return
            cmd = self._command()
            self.logs.append("Starte FFmpeg …")
            self.process = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                text=True, bufsize=1,
            )
            self.started_at = time.time()
            threading.Thread(target=self._read_logs, daemon=True).start()

    def _read_logs(self) -> None:
        proc = self.process
        if not proc or not proc.stderr:
            return
        for line in proc.stderr:
            self.logs.append(line.rstrip())
        code = proc.wait()
        self.logs.append(f"FFmpeg beendet (Code {code})")

    def stop(self) -> None:
        with self._lock:
            if not self.is_running():
                return
            assert self.process is not None
            self.process.terminate()
            try:
                self.process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.logs.append("Stream gestoppt")
            self.started_at = None

    def restart(self) -> None:
        self.stop()
        time.sleep(1)
        self.start()

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def uptime(self) -> int:
        return int(time.time() - self.started_at) if self.is_running() and self.started_at else 0
