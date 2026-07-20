from __future__ import annotations

import re
import subprocess
import threading
import time
from collections import deque
from pathlib import Path

from .profiles import apply_profile, lower_profile


class StreamManager:
    def __init__(self, config: dict):
        self.config = config
        self.process: subprocess.Popen[str] | None = None
        self.started_at: float | None = None
        self.paused = False
        self.logs: deque[str] = deque(maxlen=300)
        self._lock = threading.Lock()
        self._manual_stop = False
        self.reconnects = 0
        self.dropped_frames = 0
        self.ffmpeg_speed: float | None = None
        self.recent_failures = 0
        self._failure_times: deque[float] = deque(maxlen=20)

    @staticmethod
    def _overlay_position(name: str, margin: int = 20) -> tuple[str, str]:
        positions = {"top_left": (str(margin), str(margin)), "top_right": (f"W-w-{margin}", str(margin)), "bottom_left": (str(margin), f"H-h-{margin}"), "bottom_right": (f"W-w-{margin}", f"H-h-{margin}")}
        return positions.get(name, positions["top_right"])

    @staticmethod
    def _text_position(name: str, margin: int = 20) -> tuple[str, str]:
        positions = {"top_left": (str(margin), str(margin)), "top_right": (f"w-text_w-{margin}", str(margin)), "bottom_left": (str(margin), f"h-text_h-{margin}"), "bottom_right": (f"w-text_w-{margin}", f"h-text_h-{margin}")}
        return positions.get(name, positions["bottom_left"])

    @staticmethod
    def _escape_drawtext(value: str) -> str:
        return value.replace("\\", r"\\").replace("'", r"\'").replace(":", r"\:").replace("%", r"\%").replace("[", r"\[").replace("]", r"\]")

    @staticmethod
    def _stream_target(stream: dict) -> tuple[str, str]:
        platform = str(stream.get("platform", "youtube")).lower()
        labels = {"youtube": "YouTube", "twitch": "Twitch", "custom": "RTMP"}
        urls = {"youtube": str(stream.get("youtube_url", "rtmp://a.rtmp.youtube.com/live2")), "twitch": str(stream.get("twitch_url", "rtmp://live.twitch.tv/app")), "custom": str(stream.get("custom_url", ""))}
        if platform not in urls:
            raise ValueError("Unbekannte Streaming-Plattform")
        server_url = urls[platform].strip()
        stream_key = str(stream.get("stream_key", "")).strip()
        if not server_url:
            raise ValueError("RTMP-Serveradresse fehlt")
        if not server_url.lower().startswith(("rtmp://", "rtmps://")):
            raise ValueError("Serveradresse muss mit rtmp:// oder rtmps:// beginnen")
        if not stream_key:
            raise ValueError(f"{labels[platform]}-Stream-Key fehlt")
        return labels[platform], f"{server_url.rstrip('/')}/{stream_key.lstrip('/')}"

    def _clean_recordings(self, directory: Path, max_storage_gb: int) -> None:
        limit = max_storage_gb * 1024 * 1024 * 1024
        files = sorted((p for p in directory.glob("*.mkv") if p.is_file()), key=lambda p: p.stat().st_mtime)
        total = sum(p.stat().st_size for p in files)
        for path in files:
            if total <= limit:
                break
            try:
                size = path.stat().st_size
                path.unlink()
                total -= size
                self.logs.append(f"Alte Aufnahme gelöscht: {path.name}")
            except OSError as exc:
                self.logs.append(f"Aufnahme konnte nicht gelöscht werden: {exc}")

    def _output_args(self, target: str) -> list[str]:
        recording = self.config.get("recording", {})
        if not recording.get("enabled"):
            return ["-f", "flv", target]
        directory = Path(str(recording.get("path", "/opt/pistreamer/data/recordings"))).expanduser()
        directory.mkdir(parents=True, exist_ok=True)
        if recording.get("delete_oldest", True):
            self._clean_recordings(directory, max(1, int(recording.get("max_storage_gb", 20))))
        segment_seconds = max(10, int(recording.get("segment_seconds", 60)))
        filename = directory / "pistreamer-%Y%m%d-%H%M%S.mkv"
        tee = f"[f=flv:onfail=ignore]{target}|[f=segment:segment_time={segment_seconds}:reset_timestamps=1:strftime=1:onfail=ignore]{filename}"
        self.logs.append(f"Sicherheitsaufnahme aktiv: {directory}")
        return ["-f", "tee", tee]

    def _command(self) -> list[str]:
        s = self.config["stream"]
        overlay = self.config.get("overlay", {})
        platform_label, target = self._stream_target(s)
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "info", "-stats"]
        if self.paused:
            pause_path = Path(str(self.config.get("pause_screen", {}).get("image_path", ""))).expanduser()
            if not pause_path.is_file():
                raise ValueError(f"Pausenbild nicht gefunden: {pause_path}")
            cmd += ["-loop", "1", "-framerate", str(s["fps"]), "-i", str(pause_path), "-f", "alsa", "-i", s["audio_device"], "-vf", f"scale={s['width']}:{s['height']}:force_original_aspect_ratio=decrease,pad={s['width']}:{s['height']}:(ow-iw)/2:(oh-ih)/2,format=yuv420p", "-map", "0:v:0", "-map", "1:a:0"]
        else:
            cmd += ["-f", "v4l2", "-framerate", str(s["fps"]), "-video_size", f"{s['width']}x{s['height']}", "-i", s["video_device"]]
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
                filters.append(f"{current_video}drawtext=text='{text}':x={x}:y={y}:fontsize={size}:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=10[{output_label}]")
            elif logo_enabled:
                filters.append(f"{current_video}null[{output_label}]")
            if filters:
                cmd += ["-filter_complex", ";".join(filters), "-map", f"[{output_label}]", "-map", f"{audio_input_index}:a:0"]
            else:
                cmd += ["-map", "0:v:0", "-map", "1:a:0"]
        bitrate = str(s.get("video_bitrate", "2500k"))
        maxrate = str(s.get("maxrate", bitrate))
        buffer_size = str(s.get("buffer_size", "5000k"))
        cmd += ["-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency", "-profile:v", "high", "-level", "4.1", "-b:v", bitrate, "-maxrate", maxrate, "-bufsize", buffer_size, "-pix_fmt", "yuv420p", "-g", str(int(s["fps"]) * 2), "-keyint_min", str(int(s["fps"]) * 2), "-sc_threshold", "0", "-c:a", "aac", "-b:a", s["audio_bitrate"], "-ar", "44100", "-shortest", "-flush_packets", "1"]
        cmd += self._output_args(target)
        self.logs.append(f"Streaming-Ziel: {platform_label}")
        self.logs.append(f"Profil: {s.get('quality_profile', 'custom')} · {s['width']}x{s['height']}@{s['fps']} · {bitrate}")
        return cmd

    def start(self) -> None:
        with self._lock:
            if self.is_running():
                return
            self._manual_stop = False
            cmd = self._command()
            self.logs.append("Starte Pausenbild …" if self.paused else "Starte FFmpeg …")
            self.process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, bufsize=1)
            self.started_at = time.time()
            threading.Thread(target=self._read_logs, args=(self.process,), daemon=True).start()

    def _parse_stats(self, line: str) -> None:
        drop = re.search(r"drop=\s*(\d+)", line)
        if drop:
            self.dropped_frames = max(self.dropped_frames, int(drop.group(1)))
        speed = re.search(r"speed=\s*([0-9.]+)x", line)
        if speed:
            self.ffmpeg_speed = float(speed.group(1))

    def _read_logs(self, proc: subprocess.Popen[str]) -> None:
        if not proc.stderr:
            return
        for line in proc.stderr:
            clean = line.rstrip()
            self._parse_stats(clean)
            self.logs.append(clean)
        code = proc.wait()
        self.logs.append(f"FFmpeg beendet (Code {code})")
        if self.process is proc:
            self.started_at = None
        stream = self.config.get("stream", {})
        if not self._manual_stop:
            now = time.monotonic()
            self._failure_times.append(now)
            self.recent_failures = sum(1 for stamp in self._failure_times if now - stamp <= 120)
            if stream.get("auto_quality", False) and self.recent_failures >= 2:
                current = str(stream.get("quality_profile", "mobile_standard"))
                fallback = lower_profile(current)
                if fallback != current and apply_profile(stream, fallback):
                    self.logs.append(f"Automatische Qualitätsanpassung: {current} → {fallback}")
                    self.recent_failures = 0
        if not self._manual_stop and stream.get("reconnect_enabled", True):
            self.reconnects += 1
            delay = max(1, int(stream.get("reconnect_delay", 3)))
            self.logs.append(f"Neuer Verbindungsversuch in {delay} Sekunden …")
            time.sleep(delay)
            if not self._manual_stop and not self.is_running():
                try:
                    self.start()
                except Exception as exc:
                    self.logs.append(f"Wiederverbindung fehlgeschlagen: {exc}")

    def _stop_process(self) -> None:
        if not self.is_running():
            return
        assert self.process is not None
        self.process.terminate()
        try:
            self.process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            self.process.kill()
        self.started_at = None

    def stop(self) -> None:
        self._manual_stop = True
        with self._lock:
            self._stop_process()
            self.paused = False
            self.logs.append("Stream gestoppt")

    def restart(self) -> None:
        self._manual_stop = True
        with self._lock:
            self._stop_process()
        time.sleep(1)
        self.start()

    def pause(self) -> None:
        if not self.is_running():
            raise ValueError("Stream läuft nicht")
        self.paused = True
        self.logs.append("Wechsle zum Pausenbild …")
        self.restart()

    def resume(self) -> None:
        if not self.is_running():
            raise ValueError("Stream läuft nicht")
        self.paused = False
        self.logs.append("Wechsle zurück zur Kamera …")
        self.restart()

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def uptime(self) -> int:
        return int(time.time() - self.started_at) if self.is_running() and self.started_at else 0
