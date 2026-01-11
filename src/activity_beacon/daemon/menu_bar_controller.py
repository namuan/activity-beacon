"""MenuBarController - System tray interface for ActivityBeacon capture daemon."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from activity_beacon.logging import get_logger

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QApplication

logger = get_logger("activity_beacon.daemon.menu_bar_controller")


class MenuBarController:
    """
    System tray controller for ActivityBeacon.

    Provides a menu bar interface to control the capture daemon:
    - Start/stop capture
    - Configure capture interval
    - Display current status and statistics
    """

    def __init__(self, app: QApplication) -> None:  # type: ignore[reportMissingSuperCall]
        """
        Initialize the menu bar controller.

        Args:
            app: The QApplication instance
        """
        self._app = app
        self._is_capturing = False
        self._capture_interval_seconds = 30
        self._capture_count = 0
        self._last_error_msg: str | None = None

        # Create system tray icon
        self._tray_icon = QSystemTrayIcon()
        self._setup_icon()
        self._setup_menu()

        # Timer for periodic updates (update status every 5 seconds)
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_status_display)  # type: ignore[reportUnknownMemberType]
        self._update_timer.start(5000)  # 5 seconds

        logger.info("MenuBarController initialized")

    def _setup_icon(self) -> None:
        """Set up the system tray icon."""
        # Try to load the icon from assets
        icon_path = Path(__file__).parent.parent.parent.parent / "assets" / "icon.icns"
        if icon_path.exists():
            icon = QIcon(str(icon_path))
            self._tray_icon.setIcon(icon)
            logger.debug("Loaded icon from %s", icon_path)
        else:
            # Fall back to a system icon
            logger.warning("Icon not found at %s, using default", icon_path)

        self._tray_icon.setToolTip("ActivityBeacon - Not Running")

    def _setup_menu(self) -> None:
        """Set up the system tray menu."""
        menu = QMenu()

        # Start/Stop action
        self._start_stop_action = QAction("Start Capture")
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
            action = QAction(label)
            action.triggered.connect(  # type: ignore[reportUnknownMemberType]
                lambda _checked=False, s=seconds: self._set_interval(s)
            )
            config_menu.addAction(action)  # type: ignore[reportUnknownMemberType,reportOptionalMemberAccess]

        menu.addSeparator()

        # Status display (non-clickable)
        self._status_action = QAction("Status: Not Running")
        self._status_action.setEnabled(False)
        menu.addAction(self._status_action)  # type: ignore[reportUnknownMemberType]

        self._stats_action = QAction("Captures: 0")
        self._stats_action.setEnabled(False)
        menu.addAction(self._stats_action)  # type: ignore[reportUnknownMemberType]

        menu.addSeparator()

        # Quit action
        quit_action = QAction("Quit")
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
        self._update_status_display()

        # TODO: Wire up to actual CaptureController when US-016 is implemented
        # For now, just track the state

    def _stop_capture(self) -> None:
        """Stop the capture process."""
        self._is_capturing = False
        self._start_stop_action.setText("Start Capture")
        self._tray_icon.setToolTip("ActivityBeacon - Not Running")
        logger.info("Capture stopped")
        self._update_status_display()

        # TODO: Wire up to actual CaptureController when US-016 is implemented

    def _set_interval(self, seconds: int) -> None:
        """
        Set the capture interval.

        Args:
            seconds: Capture interval in seconds
        """
        old_interval = self._capture_interval_seconds
        self._capture_interval_seconds = seconds
        logger.info("Capture interval changed from %ds to %ds", old_interval, seconds)

        # Update tooltip if currently capturing
        if self._is_capturing:
            self._tray_icon.setToolTip(
                f"ActivityBeacon - Capturing (every {self._capture_interval_seconds}s)"
            )

        # TODO: Update CaptureController interval when US-016 is implemented

    def _update_status_display(self) -> None:
        """Update the status and statistics display in the menu."""
        if self._is_capturing:
            status_text = f"Status: Capturing (every {self._capture_interval_seconds}s)"
        else:
            status_text = "Status: Not Running"

        self._status_action.setText(status_text)
        self._stats_action.setText(f"Captures: {self._capture_count}")

        if self._last_error_msg:
            # Show error in tooltip
            self._tray_icon.setToolTip(
                f"ActivityBeacon - Error: {self._last_error_msg}"
            )

    def _quit_application(self) -> None:
        """Quit the application."""
        logger.info("Quitting application")
        if self._is_capturing:
            self._stop_capture()
        self._app.quit()

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

    @property
    def capture_count(self) -> int:
        """Return the total number of captures."""
        return self._capture_count

    def increment_capture_count(self) -> None:
        """Increment the capture counter (called by CaptureController)."""
        self._capture_count += 1
        self._update_status_display()

    def set_error(self, error_msg: str) -> None:
        """
        Set an error message to display.

        Args:
            error_msg: The error message to display
        """
        self._last_error_msg = error_msg
        self._update_status_display()
        logger.error("Error set: %s", error_msg)

    def clear_error(self) -> None:
        """Clear the error message."""
        self._last_error_msg = None
        self._update_status_display()
