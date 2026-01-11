"""CaptureController - Coordinates all components for the screenshot capture pipeline."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Event, Thread
from typing import TYPE_CHECKING

from PIL import Image

from activity_beacon.file_storage.date_directory_manager import DateDirectoryManager
from activity_beacon.file_storage.jsonl_writer import JSONLWriter
from activity_beacon.logging import get_logger
from activity_beacon.screenshot.capture import ScreenshotCapture
from activity_beacon.screenshot.change_detector import ChangeDetector
from activity_beacon.screenshot.image_processor import ImageProcessor
from activity_beacon.system_state.system_state_monitor import SystemStateMonitor
from activity_beacon.window_tracking.data import (
    FocusedAppData,
    WindowDataEntry,
    WindowInfo,
)
from activity_beacon.window_tracking.focus_tracker import FocusTracker
from activity_beacon.window_tracking.window_enumerator import WindowEnumerator

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_logger("activity_beacon.daemon")


@dataclass(frozen=True)
class CaptureConfig:
    """Configuration for the capture controller."""

    output_directory: Path
    capture_interval_seconds: int = 30
    change_threshold: int = 10
    save_all_captures: bool = False


class CaptureController:
    """Orchestrates the screenshot capture pipeline.

    This class coordinates all components to provide a complete screenshot capture
    solution with the following features:
    - Multi-monitor screenshot capture
    - Image stitching for multi-monitor setups
    - Change detection to skip unchanged screens
    - Window tracking and focus detection
    - Organized file storage with date-based directories
    - JSONL-based window data storage
    - Screen lock detection with automatic pause/resume
    - Timer-based capture cycles
    """

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        config: CaptureConfig,
        screenshot_capture: ScreenshotCapture | None = None,
        image_processor: ImageProcessor | None = None,
        change_detector: ChangeDetector | None = None,
        focus_tracker: FocusTracker | None = None,
        window_enumerator: WindowEnumerator | None = None,
        date_directory_manager: DateDirectoryManager | None = None,
        jsonl_writer: JSONLWriter | None = None,  # noqa: ARG002
        system_state_monitor: SystemStateMonitor | None = None,
    ) -> None:
        """Initialize the capture controller.

        Args:
            config: Configuration for the capture controller.
            screenshot_capture: Optional ScreenshotCapture instance.
            image_processor: Optional ImageProcessor instance.
            change_detector: Optional ChangeDetector instance.
            focus_tracker: Optional FocusTracker instance.
            window_enumerator: Optional WindowEnumerator instance.
            date_directory_manager: Optional DateDirectoryManager instance.
            jsonl_writer: Optional JSONLWriter instance.
            system_state_monitor: Optional SystemStateMonitor instance.
        """
        self._config = config
        self._last_error_msg: str | None = None

        self._screenshot_capture = screenshot_capture or ScreenshotCapture()
        self._image_processor = image_processor or ImageProcessor()
        self._change_detector = change_detector or ChangeDetector(
            threshold=config.change_threshold
        )
        self._focus_tracker = focus_tracker or FocusTracker()
        self._window_enumerator = window_enumerator or WindowEnumerator()
        self._date_directory_manager = date_directory_manager or DateDirectoryManager(
            config.output_directory
        )
        self._jsonl_writer: JSONLWriter | None = None
        self._system_state_monitor = system_state_monitor or SystemStateMonitor()

        self._is_running = False
        self._is_paused = False
        self._capture_count = 0
        self._previous_composite: Image.Image | None = None
        self._capture_thread: Thread | None = None
        self._stop_event = Event()

        self._on_start_callbacks: list[Callable[[], None]] = []
        self._on_stop_callbacks: list[Callable[[], None]] = []
        self._on_capture_callbacks: list[Callable[[int], None]] = []
        self._on_pause_callbacks: list[Callable[[], None]] = []
        self._on_resume_callbacks: list[Callable[[], None]] = []

        logger.info("CaptureController initialized")

    @property
    def last_error_msg(self) -> str | None:
        """Return the last error message, if any."""
        return self._last_error_msg

    @property
    def is_running(self) -> bool:
        """Return whether the capture controller is currently running."""
        return self._is_running

    @property
    def is_paused(self) -> bool:
        """Return whether the capture controller is currently paused."""
        return self._is_paused

    @property
    def capture_count(self) -> int:
        """Return the total number of captures performed."""
        return self._capture_count

    @property
    def capture_interval_seconds(self) -> int:
        """Return the current capture interval in seconds."""
        return self._config.capture_interval_seconds

    def set_capture_interval(self, seconds: int) -> None:
        """Set the capture interval.

        Args:
            seconds: New capture interval in seconds (must be positive).
        """
        if seconds <= 0:
            msg = "Capture interval must be positive"
            logger.error(msg)
            self._last_error_msg = msg
            raise ValueError(msg)

        old_interval = self._config.capture_interval_seconds
        self._config = CaptureConfig(
            output_directory=self._config.output_directory,
            capture_interval_seconds=seconds,
            change_threshold=self._config.change_threshold,
            save_all_captures=self._config.save_all_captures,
        )
        logger.info("Capture interval changed from %ds to %ds", old_interval, seconds)

    def add_on_start_callback(self, callback: "Callable[[], None]") -> None:
        """Add a callback to be called when capture starts.

        Args:
            callback: Function to call when capture starts.
        """
        self._on_start_callbacks.append(callback)

    def add_on_stop_callback(self, callback: "Callable[[], None]") -> None:
        """Add a callback to be called when capture stops.

        Args:
            callback: Function to call when capture stops.
        """
        self._on_stop_callbacks.append(callback)

    def add_on_capture_callback(self, callback: "Callable[[int], None]") -> None:
        """Add a callback to be called after each successful capture.

        Args:
            callback: Function to call after capture, receives capture count.
        """
        self._on_capture_callbacks.append(callback)

    def add_on_pause_callback(self, callback: "Callable[[], None]") -> None:
        """Add a callback to be called when capture is paused.

        Args:
            callback: Function to call when capture is paused.
        """
        self._on_pause_callbacks.append(callback)

    def add_on_resume_callback(self, callback: "Callable[[], None]") -> None:
        """Add a callback to be called when capture is resumed.

        Args:
            callback: Function to call when capture is resumed.
        """
        self._on_resume_callbacks.append(callback)

    def start(self) -> None:
        """Start the capture controller.

        This begins the timer-based capture cycle in a background thread.
        """
        if self._is_running:
            logger.warning("Capture controller is already running")
            return

        self._is_running = True
        self._is_paused = False
        self._stop_event.clear()

        self._system_state_monitor.set_callbacks(
            pause_callback=self._handle_pause,
            resume_callback=self._handle_resume,
        )

        self._capture_thread = Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()

        for callback in self._on_start_callbacks:
            try:
                callback()
            except Exception as e:  # noqa: BLE001
                logger.error("Error in start callback: %s", e)

        logger.info("Capture controller started")

    def stop(self) -> None:
        """Stop the capture controller.

        This stops the capture cycle and waits for the background thread to finish.
        """
        if not self._is_running:
            logger.warning("Capture controller is not running")
            return

        self._is_running = False
        self._stop_event.set()

        if self._capture_thread is not None:
            self._capture_thread.join(timeout=5.0)

        self._screenshot_capture.close()

        for callback in self._on_stop_callbacks:
            try:
                callback()
            except Exception as e:  # noqa: BLE001
                logger.error("Error in stop callback: %s", e)

        logger.info("Capture controller stopped")

    def _handle_pause(self) -> None:
        """Handle screen lock pause."""
        self._is_paused = True
        logger.info("Capture paused due to screen lock")

        for callback in self._on_pause_callbacks:
            try:
                callback()
            except Exception as e:  # noqa: BLE001
                logger.error("Error in pause callback: %s", e)

    def _handle_resume(self) -> None:
        """Handle screen unlock resume."""
        self._is_paused = False
        logger.info("Capture resumed after screen unlock")

        for callback in self._on_resume_callbacks:
            try:
                callback()
            except Exception as e:  # noqa: BLE001
                logger.error("Error in resume callback: %s", e)

    def _capture_loop(self) -> None:
        """Main capture loop running in background thread."""
        while not self._stop_event.is_set():
            try:
                self._system_state_monitor.check_and_notify()

                if not self._is_paused:
                    self._perform_capture()

            except Exception as e:  # noqa: BLE001
                error_msg = f"Error in capture loop: {e}"
                logger.error(error_msg)
                self._last_error_msg = error_msg

            self._stop_event.wait(self._config.capture_interval_seconds)

    def _perform_capture(self) -> None:
        """Perform a single capture cycle."""
        timestamp = datetime.now(UTC)

        try:
            focused_app = self._focus_tracker.get_focused_application()
            focused_pid = focused_app.pid

            all_windows = self._window_enumerator.enumerate_windows(focused_pid)

            monitor_captures = self._screenshot_capture.capture_all_monitors()

            composite = self._image_processor.stitch_horizontally(monitor_captures)

            should_save = (
                self._previous_composite is None
                or self._change_detector.has_changed(
                    self._previous_composite, composite
                )
            )

            if not should_save and not self._config.save_all_captures:
                logger.debug("Skipping save - no significant changes detected")
                return

            screenshot_path = self._save_screenshot(timestamp, composite)

            window_entry = self._create_window_data_entry(
                timestamp, focused_app, all_windows, screenshot_path
            )
            self._save_window_data(window_entry)

            self._previous_composite = composite
            self._capture_count += 1

            self._invoke_capture_callbacks()

            logger.info("Capture completed: %s", screenshot_path)

        except Exception as e:  # noqa: BLE001
            error_msg = f"Capture failed: {e}"
            logger.error(error_msg)
            self._last_error_msg = error_msg

    def _invoke_capture_callbacks(self) -> None:
        """Invoke all capture callbacks."""
        for callback in self._on_capture_callbacks:
            try:
                callback(self._capture_count)
            except Exception as e:  # noqa: BLE001
                logger.error("Error in capture callback: %s", e)

    def _save_screenshot(self, timestamp: datetime, image: Image.Image) -> str:
        """Save a screenshot to the output directory.

        Args:
            timestamp: Timestamp for the screenshot.
            image: The screenshot image to save.

        Returns:
            The path to the saved screenshot as a string.
        """
        screenshot_path = self._date_directory_manager.get_screenshot_path(timestamp)

        image.save(screenshot_path, format="PNG")
        logger.debug("Saved screenshot: %s", screenshot_path)

        return str(screenshot_path)

    @staticmethod
    def _create_window_data_entry(
        timestamp: datetime,
        focused_app: FocusedAppData,
        all_windows: tuple[WindowInfo, ...],
        screenshot_path: str,
    ) -> WindowDataEntry:
        """Create a window data entry for the current capture.

        Args:
            timestamp: Timestamp of the capture.
            focused_app: The currently focused application.
            all_windows: All visible windows.
            screenshot_path: Path to the saved screenshot.

        Returns:
            A WindowDataEntry with all the captured data.
        """
        return WindowDataEntry(
            timestamp=timestamp,
            focused_app=focused_app,
            all_windows=all_windows,
            screenshot_path=screenshot_path,
        )

    def _save_window_data(self, entry: WindowDataEntry) -> None:
        """Save window data to the JSONL file.

        Args:
            entry: The window data entry to save.
        """
        date_dir = self._date_directory_manager.ensure_date_directory(entry.timestamp)
        jsonl_path = date_dir / "window_data.jsonl"

        if (
            self._jsonl_writer is None
            or self._jsonl_writer.get_file_path() != jsonl_path
        ):
            self._jsonl_writer = JSONLWriter(jsonl_path)

        serializable_entry = self._serialize_window_data_entry(entry)
        self._jsonl_writer.write(serializable_entry)

        logger.debug("Saved window data: %s", jsonl_path)

    @staticmethod
    def _serialize_window_data_entry(
        entry: WindowDataEntry,
    ) -> dict[str, object]:
        """Serialize a WindowDataEntry to a dictionary for JSON storage.

        Args:
            entry: The window data entry to serialize.

        Returns:
            A dictionary suitable for JSON serialization.
        """
        return {
            "timestamp": entry.timestamp.isoformat(),
            "focused_app": {
                "app_name": entry.focused_app.app_name,
                "pid": entry.focused_app.pid,
                "window_name": entry.focused_app.window_name,
                "timestamp": entry.focused_app.timestamp.isoformat(),
            },
            "all_windows": [
                {
                    "window_name": w.window_name,
                    "app_name": w.app_name,
                    "pid": w.pid,
                    "is_focused": w.is_focused,
                    "screen_rect": w.screen_rect,
                }
                for w in entry.all_windows
            ],
            "screenshot_path": entry.screenshot_path,
        }

    def get_status(self) -> dict[str, object]:
        """Get the current status of the capture controller.

        Returns:
            A dictionary containing the current status.
        """
        return {
            "is_running": self._is_running,
            "is_paused": self._is_paused,
            "capture_count": self._capture_count,
            "capture_interval_seconds": self._config.capture_interval_seconds,
            "change_threshold": self._config.change_threshold,
            "save_all_captures": self._config.save_all_captures,
            "last_error_msg": self._last_error_msg,
            "system_state": self._system_state_monitor.get_state_description(),
        }

    def force_capture(self) -> None:
        """Force an immediate capture, bypassing the timer.

        This is useful for manual capture triggers.
        """
        if not self._is_running:
            msg = "Cannot force capture - controller is not running"
            logger.error(msg)
            self._last_error_msg = msg
            raise RuntimeError(msg)

        if self._is_paused:
            logger.warning("Cannot force capture - controller is paused")
            return

        self._perform_capture()

    def clear_previous_capture(self) -> None:
        """Clear the previous composite image.

        This will force the next capture to be saved regardless of changes.
        """
        self._previous_composite = None
        logger.debug("Cleared previous composite image")
