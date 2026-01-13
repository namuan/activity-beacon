"""MenuBarController - System tray interface for ActivityBeacon capture daemon."""

from __future__ import annotations

from pathlib import Path
import subprocess  # noqa: S404
import sys
from typing import TYPE_CHECKING

from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from activity_beacon.daemon.preferences_dialog import PreferencesDialog
from activity_beacon.logging import get_default_log_dir, get_logger

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QApplication

    from activity_beacon.daemon.capture_controller import CaptureController

logger = get_logger("activity_beacon.daemon.menu_bar_controller")


class MenuBarController:
    """
    System tray controller for ActivityBeacon.

    Provides a menu bar interface to control the capture daemon:
    - Start/stop capture
    - Configure capture interval
    - Display current status and statistics
    """

    def __init__(
        self, app: QApplication, controller: CaptureController | None = None
    ) -> None:
        """
        Initialize the menu bar controller.

        Args:
            app: The QApplication instance
            controller: Optional CaptureController to control
        """
        self._app = app
        self._controller = controller
        self._is_capturing = False
        self._capture_interval_seconds = 30
        self._output_directory: Path | None = None
        self._viewer_window = None  # Lazy-loaded viewer window

        # Create system tray icon
        self._tray_icon = QSystemTrayIcon()
        self._setup_icon()
        self._setup_menu()

        logger.info("MenuBarController initialized")

    def _setup_icon(self) -> None:
        """Set up the system tray icon."""
        # Determine the base path (works in both dev and packaged modes)
        if getattr(sys, "frozen", False):
            # Running in a PyInstaller bundle
            # In a macOS app bundle, resources are in Contents/Resources
            base_path = Path(sys._MEIPASS)  # type: ignore[attr-defined]
            # Check both MacOS and Resources locations
            icon_path = base_path / "assets" / "icon.icns"
            if not icon_path.exists():
                # Try the Resources directory (PyInstaller puts data here)
                base_path = Path(sys.executable).parent.parent / "Resources"
                icon_path = base_path / "assets" / "icon.icns"
        else:
            # Running in development mode
            base_path = Path(__file__).parent.parent.parent.parent
            icon_path = base_path / "assets" / "icon.icns"

        icon = QIcon()

        if icon_path.exists():
            icon = QIcon(str(icon_path))
            logger.debug("Loaded icon from %s", icon_path)

        # If icon is still null/empty, create a simple colored icon as fallback
        if icon.isNull():
            pixmap = QPixmap(64, 64)
            pixmap.fill(QColor("transparent"))
            painter = QPainter(pixmap)
            painter.setBrush(QColor("#4A90E2"))
            painter.setPen(QColor("#2E5C8A"))
            painter.drawEllipse(8, 8, 48, 48)
            painter.end()
            icon = QIcon(pixmap)
            logger.warning("Icon not found at %s, using fallback", icon_path)

        self._tray_icon.setIcon(icon)
        self._tray_icon.setToolTip("ActivityBeacon - Not Running")

    def _setup_menu(self) -> None:
        """Set up the system tray menu."""
        menu = QMenu()

        # Start/Stop action
        self._start_stop_action = QAction("Start Capture", menu)
        self._start_stop_action.triggered.connect(self._toggle_capture)  # type: ignore[reportUnknownMemberType]
        menu.addAction(self._start_stop_action)  # type: ignore[reportUnknownMemberType]

        menu.addSeparator()

        # Configuration submenu
        config_menu = menu.addMenu("Configure Interval")

        # Interval options: 10s, 30s (default), 60s, 120s, 300s
        intervals = [
            ("10 seconds", 10),
            ("30 seconds (Default)", 30),
            ("60 seconds (1 minute)", 60),
            ("120 seconds (2 minutes)", 120),
            ("300 seconds (5 minutes)", 300),
        ]

        for label, seconds in intervals:
            action = QAction(label, menu)
            action.triggered.connect(  # type: ignore[reportUnknownMemberType]
                lambda _checked=False, s=seconds: self._set_interval(s)
            )
            config_menu.addAction(action)  # type: ignore[reportUnknownMemberType,reportOptionalMemberAccess]

        # Preferences action
        preferences_action = QAction("Preferences...", menu)
        preferences_action.triggered.connect(self._show_preferences)  # type: ignore[reportUnknownMemberType]
        menu.addAction(preferences_action)  # type: ignore[reportUnknownMemberType]

        menu.addSeparator()

        # Open viewer action
        open_viewer_action = QAction("Open Viewer", menu)
        open_viewer_action.triggered.connect(self._open_viewer)  # type: ignore[reportUnknownMemberType]
        menu.addAction(open_viewer_action)  # type: ignore[reportUnknownMemberType]

        menu.addSeparator()

        # Open folders actions
        open_screenshots_action = QAction("Open Screenshots Folder", menu)
        open_screenshots_action.triggered.connect(self._open_screenshots_folder)  # type: ignore[reportUnknownMemberType]
        menu.addAction(open_screenshots_action)  # type: ignore[reportUnknownMemberType]

        open_logs_action = QAction("Open Logs Folder", menu)
        open_logs_action.triggered.connect(self._open_logs_folder)  # type: ignore[reportUnknownMemberType]
        menu.addAction(open_logs_action)  # type: ignore[reportUnknownMemberType]

        menu.addSeparator()

        # Quit action
        quit_action = QAction("Quit ActivityBeacon", menu)
        quit_action.triggered.connect(self._quit_application)  # type: ignore[reportUnknownMemberType]
        menu.addAction(quit_action)  # type: ignore[reportUnknownMemberType]

        self._tray_icon.setContextMenu(menu)

    def _toggle_capture(self) -> None:
        """Toggle capture on/off."""
        if self._is_capturing:
            self._stop_capture()
        else:
            self._start_capture()

    def _start_capture(self) -> None:
        """Start the capture process."""
        self._is_capturing = True
        self._start_stop_action.setText("Stop Capture")
        self._tray_icon.setToolTip(
            f"ActivityBeacon - Capturing (every {self._capture_interval_seconds}s)"
        )
        logger.info("Capture started (interval: %ds)", self._capture_interval_seconds)

        # Start the actual capture controller
        if self._controller:
            self._controller.start()
        else:
            logger.warning("No CaptureController available to start")

    def _stop_capture(self) -> None:
        """Stop the capture process."""
        self._is_capturing = False
        self._start_stop_action.setText("Start Capture")
        self._tray_icon.setToolTip("ActivityBeacon - Not Running")
        logger.info("Capture stopped")

        # Stop the actual capture controller
        if self._controller:
            self._controller.stop()
        else:
            logger.warning("No CaptureController available to stop")

    def _set_interval(self, seconds: int) -> None:
        """
        Set the capture interval.

        Args:
            seconds: Capture interval in seconds
        """
        old_interval = self._capture_interval_seconds
        self._capture_interval_seconds = seconds
        logger.info("Capture interval changed from %ds to %ds", old_interval, seconds)

        # Save to settings
        settings = QSettings("ActivityBeacon", "ActivityBeacon")
        settings.setValue("capture/interval_seconds", seconds)
        settings.sync()

        # Update tooltip if currently capturing
        if self._is_capturing:
            self._tray_icon.setToolTip(
                f"ActivityBeacon - Capturing (every {self._capture_interval_seconds}s)"
            )

        # Update the capture controller's interval if it exists
        if self._controller:
            # Would need to add update_interval method to CaptureController
            logger.warning("Interval updated - requires restart to take effect")
        else:
            logger.debug("No CaptureController to update")

    def _quit_application(self) -> None:
        """Quit the application."""
        logger.info("Quitting application")
        if self._is_capturing:
            self._stop_capture()
        self._app.quit()

    def _show_preferences(self) -> None:
        """Show the preferences dialog."""

        dialog = PreferencesDialog()
        if dialog.exec():  # type: ignore[reportUnknownMemberType]
            logger.info("Preferences saved")
            # Reload settings if needed
            settings = QSettings("ActivityBeacon", "ActivityBeacon")
            self._capture_interval_seconds = int(
                settings.value("capture/interval_seconds", 30)
            )
        else:
            logger.debug("Preferences dialog cancelled")

    def _open_screenshots_folder(self) -> None:
        """Open the screenshots folder in Finder."""
        if self._output_directory is None:
            # Try to get it from settings
            settings = QSettings("ActivityBeacon", "ActivityBeacon")
            output_dir_str = settings.value("capture/output_directory")
            if output_dir_str:
                self._output_directory = Path(output_dir_str)

        if self._output_directory and self._output_directory.exists():
            subprocess.run(["open", str(self._output_directory)], check=False)
            logger.info("Opened screenshots folder: %s", self._output_directory)
        else:
            logger.warning("Screenshots folder not found or not set")
            self._tray_icon.showMessage(
                "ActivityBeacon",
                "Screenshots folder not found. Start capturing to create it.",
                QSystemTrayIcon.MessageIcon.Warning,
                3000,
            )

    def _open_logs_folder(self) -> None:
        """Open the logs folder in Finder."""
        log_dir = get_default_log_dir()

        if log_dir.exists():
            subprocess.run(["open", str(log_dir)], check=False)
            logger.info("Opened logs folder: %s", log_dir)
        else:
            logger.warning("Logs folder not found: %s", log_dir)
            self._tray_icon.showMessage(
                "ActivityBeacon",
                "Logs folder not found. Enable debug mode in preferences to create logs.",
                QSystemTrayIcon.MessageIcon.Warning,
                3000,
            )

    def _open_viewer(self) -> None:
        """Launch the viewer application."""
        try:
            # If viewer window already exists and is visible, just raise it
            if self._viewer_window is not None:
                self._viewer_window.show()
                self._viewer_window.raise_()
                self._viewer_window.activateWindow()
                logger.info("Viewer window raised to front")
                return

            # Lazy import to avoid circular dependency
            from activity_beacon.viewer.main import (  # noqa: PLC0415
                MainWindow as ViewerMainWindow,
            )

            # Get the output directory from settings
            settings = QSettings("ActivityBeacon", "ActivityBeacon")
            output_dir_str = settings.value("capture/output_directory")

            if output_dir_str:
                base_dir = Path(output_dir_str)
            else:
                base_dir = Path.home() / "Documents" / "Screenshots"

            # Create and show the viewer window
            self._viewer_window = ViewerMainWindow(base_dir=base_dir)
            self._viewer_window.show()
            logger.info("Launched viewer application")

            self._tray_icon.showMessage(
                "ActivityBeacon",
                "Viewer application opened",
                QSystemTrayIcon.MessageIcon.Information,
                2000,
            )
        except (ImportError, OSError, RuntimeError) as e:
            logger.error("Failed to launch viewer: %s", e)
            self._tray_icon.showMessage(
                "ActivityBeacon",
                f"Failed to launch viewer: {e}",
                QSystemTrayIcon.MessageIcon.Critical,
                3000,
            )

    def show(self) -> None:
        """Show the system tray icon."""
        self._tray_icon.show()
        logger.debug("System tray icon shown")

    def hide(self) -> None:
        """Hide the system tray icon."""
        self._tray_icon.hide()
        logger.debug("System tray icon hidden")

    @property
    def is_capturing(self) -> bool:
        """Return whether capture is currently active."""
        return self._is_capturing

    @property
    def capture_interval_seconds(self) -> int:
        """Return the current capture interval in seconds."""
        return self._capture_interval_seconds

    def set_output_directory(self, output_dir: Path) -> None:
        """Set the output directory for screenshots.

        Args:
            output_dir: Path to the output directory.
        """
        self._output_directory = output_dir
        logger.debug("Output directory set to: %s", output_dir)
