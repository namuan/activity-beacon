"""Integration tests for the complete capture cycle."""

from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

from PIL import Image
import pytest

from activity_beacon.daemon.capture_controller import CaptureConfig, CaptureController
from activity_beacon.file_storage.date_directory_manager import DateDirectoryManager
from activity_beacon.screenshot.capture import MonitorInfo, ScreenshotCapture
from activity_beacon.screenshot.change_detector import ChangeDetector
from activity_beacon.screenshot.image_processor import ImageProcessor
from activity_beacon.system_state.system_state_monitor import SystemStateMonitor
from activity_beacon.window_tracking.data import FocusedAppData, WindowInfo
from activity_beacon.window_tracking.focus_tracker import FocusTracker
from activity_beacon.window_tracking.window_enumerator import WindowEnumerator


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary output directory for captures."""
    output_dir = tmp_path / "captures"
    output_dir.mkdir()
    yield output_dir
    if output_dir.exists():
        for file in output_dir.rglob("*"):
            if file.is_file():
                file.unlink()


@pytest.fixture
def capture_config(temp_output_dir: Path) -> CaptureConfig:
    """Create a capture configuration for testing."""
    return CaptureConfig(
        output_directory=temp_output_dir,
        capture_interval_seconds=1,
        change_threshold=10,
        save_all_captures=False,
    )


@pytest.fixture
def sample_monitor_info() -> list[MonitorInfo]:
    """Create sample monitor information."""
    return [
        MonitorInfo(
            monitor_id=1,
            name="Monitor 1",
            x=0,
            y=0,
            width=1920,
            height=1080,
            is_primary=True,
        ),
    ]


@pytest.fixture
def sample_screenshot() -> Image.Image:
    """Create a sample screenshot image."""
    return Image.new("RGB", (1920, 1080), color="blue")


@pytest.fixture
def sample_composite() -> Image.Image:
    """Create a sample composite image."""
    return Image.new("RGB", (1920, 1080), color="green")


@pytest.fixture
def sample_focused_app() -> FocusedAppData:
    """Create sample focused application data."""
    return FocusedAppData(
        app_name="Safari",
        pid=12345,
        window_name="Test Page - Example Website",
        timestamp=datetime.now(UTC),
    )


@pytest.fixture
def sample_windows() -> tuple[WindowInfo, ...]:
    """Create sample window information."""
    return (
        WindowInfo(
            window_name="Test Window",
            app_name="Test App",
            pid=12345,
            is_focused=True,
            screen_rect=(0, 0, 1920, 1080),
        ),
        WindowInfo(
            window_name="Another Window",
            app_name="Other App",
            pid=67890,
            is_focused=False,
            screen_rect=(100, 100, 800, 600),
        ),
    )


@pytest.fixture(scope="function")
def mock_screenshot_capture(
    sample_screenshot: Image.Image,
) -> MagicMock:
    """Create a mock ScreenshotCapture with realistic behavior."""
    mock = MagicMock(spec=ScreenshotCapture)
    mock.capture_all_monitors.return_value = {1: sample_screenshot}
    return mock


@pytest.fixture(scope="function")
def mock_image_processor(sample_composite: Image.Image) -> MagicMock:
    """Create a mock ImageProcessor with realistic behavior."""
    mock = MagicMock(spec=ImageProcessor)
    mock.stitch_horizontally.return_value = sample_composite
    return mock


@pytest.fixture(scope="function")
def mock_change_detector() -> MagicMock:
    """Create a mock ChangeDetector."""
    mock = MagicMock(spec=ChangeDetector)
    mock.has_changed.return_value = True
    return mock


@pytest.fixture(scope="function")
def mock_focus_tracker(sample_focused_app: FocusedAppData) -> MagicMock:
    """Create a mock FocusTracker."""
    mock = MagicMock(spec=FocusTracker)
    mock.get_focused_application.return_value = sample_focused_app
    return mock


@pytest.fixture(scope="function")
def mock_window_enumerator(sample_windows: tuple[WindowInfo, ...]) -> MagicMock:
    """Create a mock WindowEnumerator."""
    mock = MagicMock(spec=WindowEnumerator)
    mock.enumerate_windows.return_value = sample_windows
    return mock


@pytest.fixture(scope="function")
def mock_date_directory_manager(
    temp_output_dir: Path,
) -> Generator[MagicMock, None, None]:
    """Create a mock DateDirectoryManager."""
    mock = MagicMock(spec=DateDirectoryManager)
    today = datetime.now(UTC)
    date_dir = (
        temp_output_dir
        / f"{today.year:04d}"
        / f"{today.month:02d}"
        / f"{today.day:02d}"
    )
    date_dir.mkdir(parents=True, exist_ok=True)
    mock.ensure_date_directory.return_value = date_dir
    mock.get_screenshot_path.return_value = (
        date_dir / f"{today.strftime("%Y%m%d_%H%M%S")}.png"
    )
    return mock


@pytest.fixture(scope="function")
def mock_system_state_monitor() -> MagicMock:
    """Create a mock SystemStateMonitor."""
    mock = MagicMock(spec=SystemStateMonitor)
    mock.is_screen_locked.return_value = False
    mock.check_and_notify.return_value = False
    mock.get_state_description.return_value = "unlocked"
    return mock


@pytest.fixture(scope="function")
def integration_controller(  # noqa: PLR0917
    capture_config: CaptureConfig,
    mock_screenshot_capture: MagicMock,
    mock_image_processor: MagicMock,
    mock_change_detector: MagicMock,
    mock_focus_tracker: MagicMock,
    mock_window_enumerator: MagicMock,
    mock_date_directory_manager: MagicMock,
    mock_system_state_monitor: MagicMock,
) -> CaptureController:
    """Create a CaptureController configured for integration testing."""
    return CaptureController(
        config=capture_config,
        screenshot_capture=mock_screenshot_capture,
        image_processor=mock_image_processor,
        change_detector=mock_change_detector,
        focus_tracker=mock_focus_tracker,
        window_enumerator=mock_window_enumerator,
        date_directory_manager=mock_date_directory_manager,
        system_state_monitor=mock_system_state_monitor,
    )


class TestCompleteCaptureCycle:
    """Integration tests for the complete capture cycle."""

    def test_controller_uses_provided_mocks(
        self,
        integration_controller: CaptureController,
        mock_screenshot_capture: MagicMock,
    ) -> None:
        """Verify that the controller uses the provided mock components."""
        assert integration_controller._screenshot_capture is mock_screenshot_capture

    def test_full_capture_workflow(
        self,
        temp_output_dir: Path,
        sample_focused_app: FocusedAppData,
        sample_windows: tuple[WindowInfo, ...],
    ) -> None:
        """Test the complete capture workflow from start to finish."""
        mock_screenshot_capture = MagicMock(spec=ScreenshotCapture)
        mock_screenshot_capture.capture_all_monitors.return_value = {
            1: Image.new("RGB", (1920, 1080), color="blue"),
        }

        mock_image_processor = MagicMock(spec=ImageProcessor)
        mock_image_processor.stitch_horizontally.return_value = Image.new(
            "RGB", (1920, 1080), color="green"
        )

        mock_change_detector = MagicMock(spec=ChangeDetector)
        mock_change_detector.has_changed.return_value = True

        mock_focus_tracker = MagicMock(spec=FocusTracker)
        mock_focus_tracker.get_focused_application.return_value = sample_focused_app

        mock_window_enumerator = MagicMock(spec=WindowEnumerator)
        mock_window_enumerator.enumerate_windows.return_value = sample_windows

        mock_date_directory_manager = MagicMock(spec=DateDirectoryManager)
        today = datetime.now(UTC)
        date_dir = (
            temp_output_dir
            / f"{today.year:04d}"
            / f"{today.month:02d}"
            / f"{today.day:02d}"
        )
        date_dir.mkdir(parents=True, exist_ok=True)
        mock_date_directory_manager.ensure_date_directory.return_value = date_dir
        mock_date_directory_manager.get_screenshot_path.return_value = (
            date_dir / f"{today.strftime("%Y%m%d_%H%M%S")}.png"
        )

        mock_system_state_monitor = MagicMock(spec=SystemStateMonitor)
        mock_system_state_monitor.is_screen_locked.return_value = False
        mock_system_state_monitor.check_and_notify.return_value = False
        mock_system_state_monitor.get_state_description.return_value = "unlocked"

        capture_complete_callback = MagicMock()

        config = CaptureConfig(
            output_directory=temp_output_dir,
            capture_interval_seconds=1,
            change_threshold=10,
            save_all_captures=False,
        )

        controller = CaptureController(
            config=config,
            screenshot_capture=mock_screenshot_capture,
            image_processor=mock_image_processor,
            change_detector=mock_change_detector,
            focus_tracker=mock_focus_tracker,
            window_enumerator=mock_window_enumerator,
            date_directory_manager=mock_date_directory_manager,
            system_state_monitor=mock_system_state_monitor,
        )

        controller.add_on_capture_callback(capture_complete_callback)

        controller.start()

        try:
            controller._perform_capture()

            assert controller.capture_count == 1
            capture_complete_callback.assert_called_once_with(1)

        finally:
            controller.stop()

    def test_screenshot_storage_integration(
        self,
        integration_controller: CaptureController,
        mock_date_directory_manager: MagicMock,
        _temp_output_dir: Path,
    ) -> None:
        """Test that screenshots are stored correctly."""
        integration_controller.start()

        try:
            integration_controller._perform_capture()

            mock_date_directory_manager.ensure_date_directory.assert_called()
            screenshot_path = (
                mock_date_directory_manager.get_screenshot_path.return_value
            )

            assert mock_date_directory_manager.ensure_date_directory.called
            assert "png" in str(screenshot_path).lower()

        finally:
            integration_controller.stop()

    def test_window_data_collection_integration(
        self,
        integration_controller: CaptureController,
        mock_focus_tracker: MagicMock,
        mock_window_enumerator: MagicMock,
        _sample_focused_app: FocusedAppData,
        _sample_windows: tuple[WindowInfo, ...],
    ) -> None:
        """Test that window data is collected correctly."""
        integration_controller.start()

        try:
            integration_controller._perform_capture()

            mock_focus_tracker.get_focused_application.assert_called()
            mock_window_enumerator.enumerate_windows.assert_called()

        finally:
            integration_controller.stop()

    def test_change_detection_integration(
        self,
        integration_controller: CaptureController,
        mock_change_detector: MagicMock,
        sample_composite: Image.Image,
    ) -> None:
        """Test that change detection works correctly."""
        integration_controller._previous_composite = sample_composite
        mock_change_detector.has_changed.return_value = False

        integration_controller._perform_capture()

        mock_change_detector.has_changed.assert_called_once()

    def test_save_all_captures_mode(  # noqa: PLR0917
        self,
        temp_output_dir: Path,
        mock_screenshot_capture: MagicMock,
        mock_image_processor: MagicMock,
        mock_change_detector: MagicMock,
        mock_focus_tracker: MagicMock,
        mock_window_enumerator: MagicMock,
        mock_date_directory_manager: MagicMock,
        mock_system_state_monitor: MagicMock,
        _sample_focused_app: FocusedAppData,
        _sample_windows: tuple[WindowInfo, ...],
        sample_composite: Image.Image,
    ) -> None:
        """Test capture with save_all_captures enabled."""
        config = CaptureConfig(
            output_directory=temp_output_dir,
            capture_interval_seconds=1,
            change_threshold=10,
            save_all_captures=True,
        )

        controller = CaptureController(
            config=config,
            screenshot_capture=mock_screenshot_capture,
            image_processor=mock_image_processor,
            change_detector=mock_change_detector,
            focus_tracker=mock_focus_tracker,
            window_enumerator=mock_window_enumerator,
            date_directory_manager=mock_date_directory_manager,
            system_state_monitor=mock_system_state_monitor,
        )

        controller._previous_composite = sample_composite
        mock_change_detector.has_changed.return_value = False

        controller.start()
        try:
            controller._perform_capture()

            assert controller.capture_count == 1
        finally:
            controller.stop()


class TestErrorRecovery:
    """Integration tests for error recovery and system state handling."""

    def test_capture_failure_recovery(
        self,
        integration_controller: CaptureController,
        mock_screenshot_capture: MagicMock,
    ) -> None:
        """Test that capture failures are handled gracefully."""
        mock_screenshot_capture.capture_all_monitors.side_effect = OSError(
            "Failed to capture screenshot"
        )

        integration_controller.start()

        try:
            integration_controller._perform_capture()

            last_error = integration_controller.last_error_msg
            assert last_error is not None
            assert "Failed to capture screenshot" in last_error

        finally:
            integration_controller.stop()

    def test_focus_tracker_failure_recovery(
        self,
        integration_controller: CaptureController,
        mock_focus_tracker: MagicMock,
    ) -> None:
        """Test that focus tracker failures are handled gracefully."""
        mock_focus_tracker.get_focused_application.side_effect = Exception(
            "Failed to get focused app"
        )

        integration_controller.start()

        try:
            integration_controller._perform_capture()

            last_error = integration_controller.last_error_msg
            assert last_error is not None
            assert "Failed to get focused app" in last_error

        finally:
            integration_controller.stop()

    def test_image_processor_failure_recovery(
        self,
        integration_controller: CaptureController,
        mock_image_processor: MagicMock,
    ) -> None:
        """Test that image processor failures are handled gracefully."""
        mock_image_processor.stitch_horizontally.side_effect = Exception(
            "Failed to stitch images"
        )

        integration_controller.start()

        try:
            integration_controller._perform_capture()

            last_error = integration_controller.last_error_msg
            assert last_error is not None
            assert "Failed to stitch images" in last_error

        finally:
            integration_controller.stop()


class TestSystemStateHandling:
    """Integration tests for system state handling."""

    def test_screen_lock_pause(
        self,
        integration_controller: CaptureController,
        mock_system_state_monitor: MagicMock,
    ) -> None:
        """Test that capture pauses when screen is locked."""
        pause_callback = MagicMock()
        integration_controller.add_on_pause_callback(pause_callback)

        mock_system_state_monitor.check_and_notify.return_value = True
        mock_system_state_monitor.is_screen_locked.return_value = True

        integration_controller._is_paused = False
        integration_controller._handle_pause()

        assert integration_controller._is_paused is True
        pause_callback.assert_called_once()

    def test_screen_unlock_resume(
        self,
        integration_controller: CaptureController,
        _mock_system_state_monitor: MagicMock,
    ) -> None:
        """Test that capture resumes when screen is unlocked."""
        resume_callback = MagicMock()
        integration_controller.add_on_resume_callback(resume_callback)

        integration_controller._is_paused = True
        integration_controller._handle_resume()

        assert integration_controller._is_paused is False
        resume_callback.assert_called_once()

    def test_system_state_monitoring(
        self,
        integration_controller: CaptureController,
        mock_system_state_monitor: MagicMock,
    ) -> None:
        """Test that system state is monitored during capture."""
        integration_controller.start()

        try:
            integration_controller._stop_event.set()

            mock_system_state_monitor.check_and_notify.assert_called()

        finally:
            if integration_controller._is_running:
                integration_controller.stop()


class TestMultiMonitorSupport:
    """Integration tests for multi-monitor support."""

    def test_multi_monitor_capture(
        self,
        temp_output_dir: Path,
        sample_focused_app: FocusedAppData,
        sample_windows: tuple[WindowInfo, ...],
    ) -> None:
        """Test capture with multiple monitors."""
        mock_screenshot_capture = MagicMock(spec=ScreenshotCapture)
        mock_screenshot_capture.capture_all_monitors.return_value = {
            1: Image.new("RGB", (1920, 1080), color="blue"),
            2: Image.new("RGB", (2560, 1440), color="red"),
        }

        mock_image_processor = MagicMock(spec=ImageProcessor)
        mock_image_processor.stitch_horizontally.return_value = Image.new(
            "RGB", (4480, 1440), color="purple"
        )

        mock_change_detector = MagicMock(spec=ChangeDetector)
        mock_change_detector.has_changed.return_value = True

        mock_focus_tracker = MagicMock(spec=FocusTracker)
        mock_focus_tracker.get_focused_application.return_value = sample_focused_app

        mock_window_enumerator = MagicMock(spec=WindowEnumerator)
        mock_window_enumerator.enumerate_windows.return_value = sample_windows

        mock_date_directory_manager = MagicMock(spec=DateDirectoryManager)
        today = datetime.now(UTC)
        date_dir = (
            temp_output_dir
            / f"{today.year:04d}"
            / f"{today.month:02d}"
            / f"{today.day:02d}"
        )
        date_dir.mkdir(parents=True, exist_ok=True)
        mock_date_directory_manager.ensure_date_directory.return_value = date_dir
        mock_date_directory_manager.get_screenshot_path.return_value = (
            date_dir / f"{today.strftime("%Y%m%d_%H%M%S")}.png"
        )

        mock_system_state_monitor = MagicMock(spec=SystemStateMonitor)
        mock_system_state_monitor.is_screen_locked.return_value = False
        mock_system_state_monitor.check_and_notify.return_value = False
        mock_system_state_monitor.get_state_description.return_value = "unlocked"

        config = CaptureConfig(
            output_directory=temp_output_dir,
            capture_interval_seconds=1,
            change_threshold=10,
            save_all_captures=False,
        )

        controller = CaptureController(
            config=config,
            screenshot_capture=mock_screenshot_capture,
            image_processor=mock_image_processor,
            change_detector=mock_change_detector,
            focus_tracker=mock_focus_tracker,
            window_enumerator=mock_window_enumerator,
            date_directory_manager=mock_date_directory_manager,
            system_state_monitor=mock_system_state_monitor,
        )

        controller._perform_capture()

        assert controller.capture_count == 1


class TestCallbackSystem:
    """Integration tests for the callback system."""

    def test_all_callbacks_integration(
        self,
        integration_controller: CaptureController,
    ) -> None:
        """Test that all callback types work together."""
        start_callback = MagicMock()
        stop_callback = MagicMock()
        capture_callback = MagicMock()
        pause_callback = MagicMock()
        resume_callback = MagicMock()

        integration_controller.add_on_start_callback(start_callback)
        integration_controller.add_on_stop_callback(stop_callback)
        integration_controller.add_on_capture_callback(capture_callback)
        integration_controller.add_on_pause_callback(pause_callback)
        integration_controller.add_on_resume_callback(resume_callback)

        integration_controller.start()
        start_callback.assert_called_once()

        integration_controller._perform_capture()
        capture_callback.assert_called_once_with(1)

        integration_controller._handle_pause()
        pause_callback.assert_called_once()

        integration_controller._handle_resume()
        resume_callback.assert_called_once()

        integration_controller.stop()
        stop_callback.assert_called_once()

    def test_callback_exception_handling(
        self,
        integration_controller: CaptureController,
    ) -> None:
        """Test that exceptions in callbacks are handled gracefully."""

        def failing_callback() -> None:
            msg: str = "Callback failed"
            raise RuntimeError(msg)

        integration_controller.add_on_start_callback(failing_callback)

        integration_controller.start()

        assert integration_controller.is_running

        integration_controller.stop()


class TestControllerStatus:
    """Integration tests for controller status and statistics."""

    def test_status_after_captures(
        self,
        temp_output_dir: Path,
        sample_focused_app: FocusedAppData,
        sample_windows: tuple[WindowInfo, ...],
    ) -> None:
        """Test that status reflects capture statistics."""
        mock_screenshot_capture = MagicMock(spec=ScreenshotCapture)
        mock_screenshot_capture.capture_all_monitors.return_value = {
            1: Image.new("RGB", (1920, 1080), color="blue"),
        }

        mock_image_processor = MagicMock(spec=ImageProcessor)
        mock_image_processor.stitch_horizontally.return_value = Image.new(
            "RGB", (1920, 1080), color="green"
        )

        mock_change_detector = MagicMock(spec=ChangeDetector)
        mock_change_detector.has_changed.return_value = True

        mock_focus_tracker = MagicMock(spec=FocusTracker)
        mock_focus_tracker.get_focused_application.return_value = sample_focused_app

        mock_window_enumerator = MagicMock(spec=WindowEnumerator)
        mock_window_enumerator.enumerate_windows.return_value = sample_windows

        mock_date_directory_manager = MagicMock(spec=DateDirectoryManager)
        today = datetime.now(UTC)
        date_dir = (
            temp_output_dir
            / f"{today.year:04d}"
            / f"{today.month:02d}"
            / f"{today.day:02d}"
        )
        date_dir.mkdir(parents=True, exist_ok=True)
        mock_date_directory_manager.ensure_date_directory.return_value = date_dir
        mock_date_directory_manager.get_screenshot_path.return_value = (
            date_dir / f"{today.strftime("%Y%m%d_%H%M%S")}.png"
        )

        mock_system_state_monitor = MagicMock(spec=SystemStateMonitor)
        mock_system_state_monitor.is_screen_locked.return_value = False
        mock_system_state_monitor.check_and_notify.return_value = False
        mock_system_state_monitor.get_state_description.return_value = "unlocked"

        config = CaptureConfig(
            output_directory=temp_output_dir,
            capture_interval_seconds=1,
            change_threshold=10,
            save_all_captures=False,
        )

        controller = CaptureController(
            config=config,
            screenshot_capture=mock_screenshot_capture,
            image_processor=mock_image_processor,
            change_detector=mock_change_detector,
            focus_tracker=mock_focus_tracker,
            window_enumerator=mock_window_enumerator,
            date_directory_manager=mock_date_directory_manager,
            system_state_monitor=mock_system_state_monitor,
        )

        for _ in range(3):
            controller._perform_capture()

        status = controller.get_status()

        assert status["capture_count"] == 3
        assert status["capture_interval_seconds"] == 1

    def test_status_with_error(
        self,
        integration_controller: CaptureController,
        mock_screenshot_capture: MagicMock,
    ) -> None:
        """Test that status reflects errors."""
        mock_screenshot_capture.capture_all_monitors.side_effect = OSError(
            "Capture failed"
        )

        integration_controller.start()
        integration_controller._perform_capture()

        status = integration_controller.get_status()

        last_error = status["last_error_msg"]
        assert last_error is not None
        assert isinstance(last_error, str)
        assert "Capture failed" in last_error

        integration_controller.stop()
