"""ActivityBeacon - macOS menu bar application for screenshot automation."""

import logging as logging_module
from pathlib import Path
import sys
from typing import NoReturn

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication

from activity_beacon.daemon.capture_controller import CaptureConfig, CaptureController
from activity_beacon.daemon.menu_bar_controller import MenuBarController
from activity_beacon.logging import get_default_log_dir, get_logger, setup_logging


def get_config_path() -> Path:
    """Get the recommended configuration path on macOS.

    Uses ~/Library/Application Support/ActivityBeacon/ per macOS guidelines.

    Returns:
        Path to the application's configuration directory.
    """
    return Path.home() / "Library" / "Application Support" / "ActivityBeacon"


def get_default_output_dir() -> Path:
    """Get the default output directory for captures.

    Returns:
        Path to the default output directory.
    """
    return Path.home() / "Documents" / "ActivityBeacon" / "data"


def load_settings(logger: logging_module.Logger) -> tuple[Path, int, bool]:
    """Load application settings from OS-native storage.

    On macOS, this uses QSettings which stores in ~/Library/Preferences.

    Args:
        logger: Logger instance for logging settings load.

    Returns:
        Tuple of (output_directory, capture_interval, debug_mode).
    """
    settings = QSettings("ActivityBeacon", "ActivityBeacon")

    output_dir = Path(
        settings.value("capture/output_directory", str(get_default_output_dir()))
    )
    interval = int(settings.value("capture/interval_seconds", 30))
    debug = bool(settings.value("general/debug_mode", defaultValue=False))

    logger.info("Loaded settings from: %s", settings.fileName())
    logger.debug("  Output directory: %s", output_dir)
    logger.debug("  Capture interval: %d seconds", interval)
    logger.debug("  Debug mode: %s", debug)

    return output_dir, interval, debug


def save_settings(
    logger: logging_module.Logger, output_dir: Path, interval: int, *, debug_mode: bool
) -> None:
    """Save application settings to OS-native storage.

    Args:
        logger: Logger instance for logging settings save.
        output_dir: Output directory for captured data.
        interval: Capture interval in seconds.
        debug_mode: Whether debug mode is enabled.
    """
    settings = QSettings("ActivityBeacon", "ActivityBeacon")
    settings.setValue("capture/output_directory", str(output_dir))
    settings.setValue("capture/interval_seconds", interval)
    settings.setValue("general/debug_mode", debug_mode)
    settings.sync()

    logger.info("Settings saved to: %s", settings.fileName())


def configure_logging(*, debug_mode: bool) -> logging_module.Logger:
    """Configure logging based on debug mode.

    Args:
        debug_mode: Whether debug mode is enabled.

    Returns:
        Configured logger instance.
    """
    log_dir = get_default_log_dir()
    setup_logging(log_dir)

    # Initialize the module-level logger after setup_logging
    logger = get_logger("activity_beacon", log_dir)

    if debug_mode:
        logging_module.getLogger().setLevel(logging_module.DEBUG)
        for handler in logging_module.getLogger().handlers:
            if isinstance(handler, logging_module.StreamHandler):
                handler.setLevel(logging_module.DEBUG)

    return logger


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
    """Main entry point for the menu bar application."""
    # Create QApplication first
    app = QApplication(sys.argv)
    app.setApplicationName("ActivityBeacon")
    app.setOrganizationName("ActivityBeacon")
    app.setQuitOnLastWindowClosed(False)  # Keep running when windows close

    # Configure logging early (with default settings) so we can log during settings load
    # We'll reconfigure if needed after loading debug setting
    logger = configure_logging(debug_mode=False)

    # Load settings
    output_dir, interval, debug = load_settings(logger)

    # Reconfigure logging if debug mode was enabled
    if debug:
        logger = configure_logging(debug_mode=True)

    # Ensure output directory exists
    output_dir = output_dir.expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Ensure config directory exists
    config_dir = get_config_path()
    config_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Starting ActivityBeacon menu bar application")
    logger.info("Configuration directory: %s", config_dir)
    logger.info("Output directory: %s", output_dir)
    logger.info("Capture interval: %d seconds", interval)
    logger.info("Debug mode: %s", "enabled" if debug else "disabled")

    # Create capture controller
    controller = create_capture_controller(output_dir, interval)

    # Create menu bar controller and wire it to the capture controller
    menu_bar = MenuBarController(app, controller)
    menu_bar.set_output_directory(output_dir)
    menu_bar.show()

    logger.info("ActivityBeacon menu bar is now active")

    # Run the Qt event loop
    exit_code = app.exec()

    # Clean shutdown
    controller.stop()
    logger.info("Shutdown complete")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
