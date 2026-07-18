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

    @staticmethod
    def _overlay_position(name: str, margin: int = 20) -> tuple[str, str]:
        positions = {
            "top_left": (str(margin), str(margin)),
            "top_right": (f"W-w-{margin}", str(margin)),
            "bottom_left": (str(margin), f"H-h-{margin}"),
            "bottom_right": (f"W-w-{margin}", f"H-h-{margin}"),
        }
        return positions.get(name, positions["top_right"])

    @staticmethod
    def _text_position(name: str, margin: int = 20) -> tuple[str, str]:
        positions = {
            "top_left": (str(margin), str(margin)),
            "top_right": (f"w-text_w-{margin}", str(margin)),
            "bottom_left": (str(margin), f"h-text_h-{margin}"),
            "bottom_right": (f"w-text_w-{margin}", f"h-text_h-{margin}"),
        }
        return positions.get(name, positions["bottom_left"])

    @staticmethod
    def _escape_drawtext(value: str) -> str:
        return (
            value.replace("\\", r"\\")
            .replace("'", r"\'")
            .replace(":", r"\:")
            .replace("%", r"\%")
            .replace("[", r"\[")
            .replace("]", r"\]")
        )

    def _command(self) -> list[str]:
        s = self.config["stream"]
        overlay = self.config.get("overlay", {})
        if not s.get("stream_key"):
            raise ValueError("YouTube-Stream-Key fehlt")

        target = f"{s['youtube_url'].rstrip('/')}/{s['stream_key']}"
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "info",
            "-f", "v4l2", "-framerate", str(s["fps"]),
            "-video_size", f"{s['width']}x{s['height']}",
            "-i", s["video_device"],
        ]

        logo_enabled = bool(overlay.get("logo_enabled"))
        logo_path = Path(str(overlay.get("logo_path", ""))).expanduser()
        if logo_enabled:
            if not logo_path.is_file():
                raise ValueError(f"Logo-Datei nicht gefunden: {logo_path}")
            cmd += ["-loop", "1", "-i", str(logo_path)]

        audio_input_index = 2 if logo_enabled else 1
        cmd += ["-f", "alsa", "-i", s["audio_device"]]

        filters: list[str] = []
        current_video = "[0:v]"
        output_label = "vout"

        if logo_enabled:
            logo_width = max(32, int(int(s["width"]) * int(overlay.get("logo_width_percent", 20)) / 100))
            x, y = self._overlay_position(str(overlay.get("logo_position", "top_right")))
            filters.append(f"[1:v]scale={logo_width}:-1[logo]")
            filters.append(f"{current_video}[logo]overlay={x}:{y}[withlogo]")
            current_video = "[withlogo]"

        text_enabled = bool(overlay.get("text_enabled")) and bool(str(overlay.get("text", "")).strip())
        if text_enabled:
            text = self._escape_drawtext(str(overlay.get("text", "")).strip())
            x, y = self._text_position(str(overlay.get("text_position", "bottom_left")))
            size = max(12, min(96, int(overlay.get("text_size", 32))))
            filters.append(
                f"{current_video}drawtext=text='{text}':x={x}:y={y}:fontsize={size}:"
                "fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=10"
                f"[{output_label}]"
            )
        elif logo_enabled:
            filters.append(f"{current_video}null[{output_label}]")

        if filters:
            cmd += ["-filter_complex", ";".join(filters), "-map", f"[{output_label}]", "-map", f"{audio_input_index}:a:0"]

        cmd += [
            "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency",
            "-b:v", s["video_bitrate"], "-maxrate", s["video_bitrate"],
            "-bufsize", "5000k", "-pix_fmt", "yuv420p",
            "-g", str(int(s["fps"]) * 2), "-keyint_min", str(int(s["fps"]) * 2),
            "-c:a", "aac", "-b:a", s["audio_bitrate"], "-ar", "44100",
            "-shortest", "-f", "flv", target,
        ]
        return cmd

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
