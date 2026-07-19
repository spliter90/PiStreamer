from __future__ import annotations

import logging
import os
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

LOG_DIR = Path("/opt/pistreamer/data/logs")
LOG_FILE = LOG_DIR / "pistreamer.log"
DEFAULT_TIMEZONE = "Europe/Berlin"


def apply_timezone(name: str | None) -> str:
    timezone = (name or DEFAULT_TIMEZONE).strip()
    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        timezone = DEFAULT_TIMEZONE
    os.environ["TZ"] = timezone
    if hasattr(time, "tzset"):
        time.tzset()
    return timezone


def configure_logging(timezone: str | None = None) -> logging.Logger:
    apply_timezone(timezone)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("pistreamer")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S %z",
    )

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger


def read_log_lines(limit: int = 300) -> list[str]:
    limit = max(1, min(2000, int(limit)))
    try:
        with LOG_FILE.open("r", encoding="utf-8", errors="replace") as handle:
            return handle.readlines()[-limit:]
    except OSError:
        return []
