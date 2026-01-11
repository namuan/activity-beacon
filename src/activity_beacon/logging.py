from datetime import datetime
import logging
from pathlib import Path
import sys
from typing import Literal

COMPONENT_LOGGERS: dict[str, logging.Logger] = {}


def get_default_log_dir() -> Path:
    """Return the default log directory: ~/.logs/activity-beacon/"""
    return Path.home() / ".logs" / "activity-beacon"


def get_logger(name: str, log_dir: Path | None = None) -> logging.Logger:
    if name in COMPONENT_LOGGERS:
        return COMPONENT_LOGGERS[name]

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    if log_dir is not None:
        log_dir = log_dir.expanduser()
        log_dir.mkdir(parents=True, exist_ok=True)

        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = log_dir / f"activity-beacon-{date_str}.log"

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))

        logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))

    logger.addHandler(console_handler)

    COMPONENT_LOGGERS[name] = logger
    return logger


def setup_logging(log_dir: Path | None = None) -> dict[str, logging.Logger]:
    loggers: dict[str, logging.Logger] = {}

    components = [
        "activity_beacon",
        "activity_beacon.screenshot",
        "activity_beacon.window_tracking",
        "activity_beacon.file_storage",
    ]

    for component in components:
        loggers[component] = get_logger(component, log_dir)

    return loggers


def get_level_name(
    level: int,
) -> Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    return logging.getLevelName(level)  # type: ignore[return-value]
