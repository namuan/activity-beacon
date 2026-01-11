import argparse
import logging as logging_module
from pathlib import Path
import signal
import sys
import time
import tomllib
from typing import NoReturn, TypedDict, cast

from activity_beacon.daemon.capture_controller import CaptureConfig, CaptureController
from activity_beacon.logging import get_default_log_dir, get_logger, setup_logging

logger = get_logger("activity_beacon")


class CaptureSectionConfig(TypedDict):
    interval: int
    output: str


class GeneralSectionConfig(TypedDict):
    debug: bool


class FileConfig(TypedDict):
    capture: CaptureSectionConfig
    general: GeneralSectionConfig


class CliArgs(TypedDict):
    interval: int
    output: Path
    debug: bool
    config: Path


def parse_args() -> CliArgs:
    """Parse command-line arguments.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        prog="activity-beacon",
        description="ActivityBeacon - A macOS-native screenshot automation tool",
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Capture interval in seconds (default: 30)",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path.home() / "Documents" / "ActivityBeacon" / "data",
        help="Output directory for screenshots and data (default: ~/Documents/ActivityBeacon/data)",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (verbose console output)",
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=Path.home() / ".config" / "activity-beacon" / "config.toml",
        help="Path to configuration file (default: ~/.config/activity-beacon/config.toml)",
    )

    parsed = parser.parse_args()

    return cast(
        "CliArgs",
        {
            "interval": parsed.interval,
            "output": parsed.output,
            "debug": parsed.debug,
            "config": parsed.config,
        },
    )


def load_config(config_path: Path) -> FileConfig:
    """Load configuration from TOML file.

    Args:
        config_path: Path to the configuration file.

    Returns:
        Dictionary containing configuration values.
    """
    config: FileConfig = {
        "capture": {"interval": 30, "output": ""},
        "general": {"debug": False},
    }

    if not config_path.exists():
        logger.debug("Config file not found: %s", config_path)
        return config

    try:
        with Path(config_path).open("rb") as f:
            raw_config = tomllib.load(f)
        logger.info("Loaded configuration from: %s", config_path)

        if "capture" in raw_config and isinstance(raw_config["capture"], dict):
            config["capture"] = raw_config["capture"]  # type: ignore[literal-required]
        if "general" in raw_config and isinstance(raw_config["general"], dict):
            config["general"] = raw_config["general"]  # type: ignore[literal-required]
    except OSError as e:
        logger.warning("Failed to load config file: %s", e)

    return config


def merge_config(cli_args: CliArgs, file_config: FileConfig) -> tuple[Path, int, bool]:
    """Merge CLI arguments with file configuration.

    CLI arguments take precedence over file configuration.

    Args:
        cli_args: Parsed CLI arguments.
        file_config: Configuration loaded from file.

    Returns:
        Tuple of (output_directory, capture_interval, debug_mode).
    """
    output_dir: Path = cli_args["output"]
    interval: int = cli_args["interval"]
    debug: bool = cli_args["debug"]

    if file_config.get("capture"):
        capture_config = file_config["capture"]
        if "interval" in capture_config:
            interval = capture_config["interval"]
        if "output" in capture_config:
            output_dir = Path(capture_config["output"])

    if file_config.get("general"):
        general_config = file_config["general"]
        if "debug" in general_config:
            debug = general_config["debug"]

    return output_dir, interval, debug


def configure_logging(*, debug_mode: bool, log_dir: Path | None = None) -> None:
    """Configure logging based on debug mode.

    Args:
        debug_mode: Whether debug mode is enabled.
        log_dir: Optional custom log directory.
    """
    if not debug_mode:
        log_dir = None
    elif log_dir is None:
        log_dir = get_default_log_dir()

    setup_logging(log_dir)

    if debug_mode:
        logging_module.getLogger().setLevel(logging_module.DEBUG)
        for handler in logging_module.getLogger().handlers:
            if isinstance(handler, logging_module.StreamHandler):
                handler.setLevel(logging_module.DEBUG)


def create_capture_controller(output_dir: Path, interval: int) -> CaptureController:
    """Create and configure the capture controller.

    Args:
        output_dir: Output directory for captured data.
        interval: Capture interval in seconds.

    Returns:
        Configured CaptureController instance.
    """
    config = CaptureConfig(
        output_directory=output_dir,
        capture_interval_seconds=interval,
    )
    return CaptureController(config)


def main() -> NoReturn:
    """Main entry point for the application."""
    args = parse_args()

    file_config = load_config(args["config"])

    output_dir, interval, debug = merge_config(args, file_config)

    configure_logging(debug_mode=debug)

    output_dir = output_dir.expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Starting ActivityBeacon")
    logger.info("Output directory: %s", output_dir)
    logger.info("Capture interval: %d seconds", interval)
    logger.info("Debug mode: %s", "enabled" if debug else "disabled")

    controller = create_capture_controller(output_dir, interval)

    shutdown_requested = False

    def handle_shutdown(signum: int, frame: object) -> None:  # noqa: ARG001
        nonlocal shutdown_requested
        sig_name = signal.Signals(signum).name
        logger.info("Received %s signal, shutting down gracefully...", sig_name)
        shutdown_requested = True

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    try:
        controller.start()
        logger.info("ActivityBeacon is running. Press Ctrl+C to stop.")

        while not shutdown_requested:
            time.sleep(1.0)

    except Exception as e:  # noqa: BLE001
        logger.error("Unexpected error: %s", e)
        controller.stop()
        sys.exit(1)

    controller.stop()
    logger.info("Shutdown complete")
    sys.exit(0)


if __name__ == "__main__":
    main()
