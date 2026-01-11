"""Tests for CaptureController."""

from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock, patch

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
def mock_screenshot_capture() -> MagicMock:
    """Create a mock ScreenshotCapture."""
    mock = MagicMock(spec=ScreenshotCapture)
    mock.enumerate_monitors.return_value = [
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
    mock.capture_all_monitors.return_value = {
        1: Image.new("RGB", (1920, 1080), color="blue")
    }
    return mock


@pytest.fixture
def mock_image_processor() -> MagicMock:
    """Create a mock ImageProcessor."""
    mock = MagicMock(spec=ImageProcessor)
    mock.stitch_horizontally.return_value = Image.new(
        "RGB", (1920, 1080), color="green"
    )
    return mock


@pytest.fixture
def mock_change_detector() -> MagicMock:
    """Create a mock ChangeDetector."""
    mock = MagicMock(spec=ChangeDetector)
    mock.has_changed.return_value = True
    return mock


@pytest.fixture
def mock_focus_tracker() -> MagicMock:
    """Create a mock FocusTracker."""
    mock = MagicMock(spec=FocusTracker)
    mock.get_focused_application.return_value = FocusedAppData(
        app_name="Safari",
        pid=12345,
        window_name="Test Page",
        timestamp=datetime.now(UTC),
    )
    return mock


@pytest.fixture
def mock_window_enumerator() -> MagicMock:
    """Create a mock WindowEnumerator."""
    mock = MagicMock(spec=WindowEnumerator)
    mock.enumerate_windows.return_value = (
        WindowInfo(
            window_name="Test Window",
            app_name="Test App",
            pid=12345,
            is_focused=True,
            screen_rect=(0, 0, 1920, 1080),
        ),
    )
    return mock


@pytest.fixture
def mock_date_directory_manager(
    tmp_path: Path,
) -> Generator[MagicMock, None, None]:
    """Create a mock DateDirectoryManager."""
    mock = MagicMock(spec=DateDirectoryManager)
    date_dir = tmp_path / "captures" / "2024" / "01" / "15"
    date_dir.mkdir(parents=True)
    mock.ensure_date_directory.return_value = date_dir
    mock.get_screenshot_path.return_value = date_dir / "20240115_103000.png"
    return mock


@pytest.fixture
def mock_system_state_monitor() -> MagicMock:
    """Create a mock SystemStateMonitor."""
    mock = MagicMock(spec=SystemStateMonitor)
    mock.is_screen_locked.return_value = False
    mock.check_and_notify.return_value = False
    mock.get_state_description.return_value = "unlocked"
    return mock


@pytest.fixture
def controller(  # noqa: PLR0917
    capture_config: CaptureConfig,
    mock_screenshot_capture: MagicMock,
    mock_image_processor: MagicMock,
    mock_change_detector: MagicMock,
    mock_focus_tracker: MagicMock,
    mock_window_enumerator: MagicMock,
    mock_date_directory_manager: MagicMock,
    mock_system_state_monitor: MagicMock,
) -> CaptureController:
    """Create a CaptureController with mocked dependencies."""
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


class TestCaptureControllerInit:
    """Tests for CaptureController initialization."""

    def test_init_with_defaults(self, capture_config: CaptureConfig) -> None:
        """Test initialization with default values."""
        controller = CaptureController(config=capture_config)

        assert controller.capture_interval_seconds == 1
        assert controller.capture_count == 0
        assert controller.is_running is False
        assert controller.is_paused is False

    def test_init_with_custom_config(self, temp_output_dir: Path) -> None:
        """Test initialization with custom configuration."""
        config = CaptureConfig(
            output_directory=temp_output_dir,
            capture_interval_seconds=60,
            change_threshold=20,
            save_all_captures=True,
        )
        controller = CaptureController(config=config)

        assert controller.capture_interval_seconds == 60

    def test_init_with_custom_components(
        self,
        capture_config: CaptureConfig,
        mock_screenshot_capture: MagicMock,
        mock_image_processor: MagicMock,
        mock_change_detector: MagicMock,
    ) -> None:
        """Test initialization with custom components."""
        controller = CaptureController(
            config=capture_config,
            screenshot_capture=mock_screenshot_capture,
            image_processor=mock_image_processor,
            change_detector=mock_change_detector,
        )

        assert controller._screenshot_capture is mock_screenshot_capture
        assert controller._image_processor is mock_image_processor
        assert controller._change_detector is mock_change_detector


class TestCaptureControllerProperties:
    """Tests for CaptureController properties."""

    def test_last_error_msg_initially_none(self, controller: CaptureController) -> None:
        """Test that last_error_msg is initially None."""
        assert controller.last_error_msg is None

    def test_is_running_initially_false(self, controller: CaptureController) -> None:
        """Test that is_running is initially False."""
        assert controller.is_running is False

    def test_is_paused_initially_false(self, controller: CaptureController) -> None:
        """Test that is_paused is initially False."""
        assert controller.is_paused is False

    def test_capture_count_initially_zero(self, controller: CaptureController) -> None:
        """Test that capture_count is initially 0."""
        assert controller.capture_count == 0


class TestCaptureControllerCallbacks:
    """Tests for CaptureController callback management."""

    def test_add_on_start_callback(self, controller: CaptureController) -> None:
        """Test adding start callbacks."""
        callback = MagicMock()
        controller.add_on_start_callback(callback)

        assert callback in controller._on_start_callbacks

    def test_add_on_stop_callback(self, controller: CaptureController) -> None:
        """Test adding stop callbacks."""
        callback = MagicMock()
        controller.add_on_stop_callback(callback)

        assert callback in controller._on_stop_callbacks

    def test_add_on_capture_callback(self, controller: CaptureController) -> None:
        """Test adding capture callbacks."""
        callback = MagicMock()
        controller.add_on_capture_callback(callback)

        assert callback in controller._on_capture_callbacks

    def test_add_on_pause_callback(self, controller: CaptureController) -> None:
        """Test adding pause callbacks."""
        callback = MagicMock()
        controller.add_on_pause_callback(callback)

        assert callback in controller._on_pause_callbacks

    def test_add_on_resume_callback(self, controller: CaptureController) -> None:
        """Test adding resume callbacks."""
        callback = MagicMock()
        controller.add_on_resume_callback(callback)

        assert callback in controller._on_resume_callbacks


class TestCaptureControllerCaptureInterval:
    """Tests for capture interval management."""

    def test_set_capture_interval_valid(self, controller: CaptureController) -> None:
        """Test setting a valid capture interval."""
        controller.set_capture_interval(120)
        assert controller.capture_interval_seconds == 120

    def test_set_capture_interval_invalid(self, controller: CaptureController) -> None:
        """Test setting an invalid capture interval."""
        with pytest.raises(ValueError, match="must be positive"):
            controller.set_capture_interval(-10)

    def test_set_capture_interval_zero(self, controller: CaptureController) -> None:
        """Test setting a zero capture interval."""
        with pytest.raises(ValueError, match="must be positive"):
            controller.set_capture_interval(0)


class TestCaptureControllerLifecycle:
    """Tests for CaptureController start/stop lifecycle."""

    def test_start_not_running(
        self,
        controller: CaptureController,
        mock_system_state_monitor: MagicMock,
    ) -> None:
        """Test starting the controller when not running."""
        controller.start()

        assert controller.is_running is True
        mock_system_state_monitor.set_callbacks.assert_called_once()

    def test_start_already_running(
        self,
        controller: CaptureController,
        mock_system_state_monitor: MagicMock,
    ) -> None:
        """Test starting the controller when already running."""
        controller.start()
        mock_system_state_monitor.reset_mock()

        controller.start()

        assert controller.is_running is True

    def test_stop_not_running(self, controller: CaptureController) -> None:
        """Test stopping the controller when not running."""
        controller.stop()

        assert controller.is_running is False

    def test_stop_running(
        self,
        controller: CaptureController,
        mock_system_state_monitor: MagicMock,  # noqa: ARG002
    ) -> None:
        """Test stopping the controller when running."""
        controller.start()
        mock_screenshot_capture = cast("MagicMock", controller._screenshot_capture)

        controller.stop()

        assert controller.is_running is False
        mock_screenshot_capture.close.assert_called_once()


class TestCaptureControllerScreenLock:
    """Tests for screen lock pause/resume functionality."""

    def test_pause_on_screen_lock(
        self,
        controller: CaptureController,
        mock_system_state_monitor: MagicMock,  # noqa: ARG002
    ) -> None:
        """Test pause callback is triggered on screen lock."""
        pause_callback = MagicMock()
        controller.add_on_pause_callback(pause_callback)

        controller._handle_pause()

        assert controller.is_paused is True
        pause_callback.assert_called_once()

    def test_resume_on_screen_unlock(
        self,
        controller: CaptureController,
        mock_system_state_monitor: MagicMock,  # noqa: ARG002
    ) -> None:
        """Test resume callback is triggered on screen unlock."""
        controller._is_paused = True
        resume_callback = MagicMock()
        controller.add_on_resume_callback(resume_callback)

        controller._handle_resume()

        assert controller.is_paused is False
        resume_callback.assert_called_once()


class TestCaptureControllerPerformCapture:
    """Tests for the capture operation."""

    def test_perform_capture_success(  # noqa: PLR0917
        self,
        controller: CaptureController,
        mock_screenshot_capture: MagicMock,
        mock_image_processor: MagicMock,
        mock_change_detector: MagicMock,  # noqa: ARG002
        mock_focus_tracker: MagicMock,
        mock_window_enumerator: MagicMock,
        mock_date_directory_manager: MagicMock,  # noqa: ARG002
        tmp_path: Path,  # noqa: ARG002
    ) -> None:
        """Test successful capture operation."""
        with patch.object(Image.Image, "save") as mock_save:
            mock_save.return_value = None
            controller._perform_capture()

            assert controller.capture_count == 1
            mock_screenshot_capture.capture_all_monitors.assert_called_once()
            mock_image_processor.stitch_horizontally.assert_called_once()
            mock_focus_tracker.get_focused_application.assert_called_once()
            mock_window_enumerator.enumerate_windows.assert_called_once()

    def test_perform_capture_with_change_detection(  # noqa: PLR0917
        self,
        controller: CaptureController,
        mock_screenshot_capture: MagicMock,  # noqa: ARG002
        mock_image_processor: MagicMock,  # noqa: ARG002
        mock_change_detector: MagicMock,
        mock_focus_tracker: MagicMock,  # noqa: ARG002
        mock_window_enumerator: MagicMock,  # noqa: ARG002
        mock_date_directory_manager: MagicMock,  # noqa: ARG002
    ) -> None:
        """Test capture with change detection skipping save."""
        with patch.object(Image.Image, "save") as mock_save:
            mock_save.return_value = None
            controller._perform_capture()
            mock_change_detector.has_changed.return_value = False

            controller._perform_capture()

            assert controller.capture_count == 1

    def test_perform_capture_with_save_all(  # noqa: PLR0917
        self,
        capture_config: CaptureConfig,
        mock_screenshot_capture: MagicMock,
        mock_image_processor: MagicMock,
        mock_change_detector: MagicMock,
        mock_focus_tracker: MagicMock,
        mock_window_enumerator: MagicMock,
        mock_date_directory_manager: MagicMock,
        mock_system_state_monitor: MagicMock,
        tmp_path: Path,  # noqa: ARG002
    ) -> None:
        """Test capture with save_all_captures=True."""
        config = CaptureConfig(
            output_directory=capture_config.output_directory,
            capture_interval_seconds=1,
            save_all_captures=True,
        )
        mock_change_detector.has_changed.return_value = False

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

        with patch.object(Image.Image, "save") as mock_save:
            mock_save.return_value = None
            controller._perform_capture()

            assert controller.capture_count == 1


class TestCaptureControllerCallbacksInvocation:
    """Tests for callback invocation during capture."""

    def test_on_start_callback_invoked(
        self,
        controller: CaptureController,
        mock_system_state_monitor: MagicMock,  # noqa: ARG002
    ) -> None:
        """Test that on_start callbacks are invoked when starting."""
        on_start = MagicMock()
        controller.add_on_start_callback(on_start)

        controller.start()

        on_start.assert_called_once()

    def test_on_stop_callback_invoked(
        self,
        controller: CaptureController,
        mock_system_state_monitor: MagicMock,  # noqa: ARG002
    ) -> None:
        """Test that on_stop callbacks are invoked when stopping."""
        on_stop = MagicMock()
        controller.add_on_stop_callback(on_stop)

        controller.start()
        controller.stop()

        on_stop.assert_called_once()

    def test_on_capture_callback_invoked(  # noqa: PLR0917
        self,
        controller: CaptureController,
        mock_screenshot_capture: MagicMock,  # noqa: ARG002
        mock_image_processor: MagicMock,  # noqa: ARG002
        mock_change_detector: MagicMock,  # noqa: ARG002
        mock_focus_tracker: MagicMock,  # noqa: ARG002
        mock_window_enumerator: MagicMock,  # noqa: ARG002
        mock_date_directory_manager: MagicMock,  # noqa: ARG002
        mock_system_state_monitor: MagicMock,  # noqa: ARG002
    ) -> None:
        """Test that on_capture callbacks are invoked after capture."""
        on_capture = MagicMock()
        controller.add_on_capture_callback(on_capture)

        with patch.object(Image.Image, "save") as mock_save:
            mock_save.return_value = None
            controller._perform_capture()

            on_capture.assert_called_once_with(1)


class TestCaptureControllerStatus:
    """Tests for status reporting."""

    def test_get_status(
        self,
        controller: CaptureController,
        capture_config: CaptureConfig,
        mock_system_state_monitor: MagicMock,  # noqa: ARG002
    ) -> None:
        """Test getting controller status."""
        status = controller.get_status()

        assert status["is_running"] is False
        assert status["is_paused"] is False
        assert status["capture_count"] == 0
        assert (
            status["capture_interval_seconds"]
            == capture_config.capture_interval_seconds
        )
        assert status["change_threshold"] == capture_config.change_threshold
        assert status["save_all_captures"] == capture_config.save_all_captures
        assert status["last_error_msg"] is None


class TestCaptureControllerForceCapture:
    """Tests for force capture functionality."""

    def test_force_capture_not_running(
        self,
        controller: CaptureController,
    ) -> None:
        """Test force capture when not running raises error."""
        with pytest.raises(RuntimeError, match="not running"):
            controller.force_capture()

    def test_force_capture_paused(
        self,
        controller: CaptureController,
        mock_system_state_monitor: MagicMock,  # noqa: ARG002
    ) -> None:
        """Test force capture when paused does nothing."""
        controller._is_running = True
        controller._is_paused = True
        mock_screenshot_capture = cast("MagicMock", controller._screenshot_capture)

        controller.force_capture()

        mock_screenshot_capture.capture_all_monitors.assert_not_called()

    def test_force_capture_running(
        self,
        controller: CaptureController,
        mock_screenshot_capture: MagicMock,
        mock_system_state_monitor: MagicMock,  # noqa: ARG002
    ) -> None:
        """Test force capture when running performs capture."""
        controller.start()
        controller._is_paused = False

        controller.force_capture()

        mock_screenshot_capture.capture_all_monitors.assert_called()


class TestCaptureControllerClearPrevious:
    """Tests for clearing previous composite image."""

    def test_clear_previous_capture(self, controller: CaptureController) -> None:
        """Test clearing previous composite image."""
        controller._previous_composite = Image.new("RGB", (100, 100))

        controller.clear_previous_capture()

        assert controller._previous_composite is None


class TestCaptureConfig:
    """Tests for CaptureConfig dataclass."""

    def test_default_values(self, temp_output_dir: Path) -> None:
        """Test CaptureConfig default values."""
        config = CaptureConfig(output_directory=temp_output_dir)

        assert config.capture_interval_seconds == 30
        assert config.change_threshold == 10
        assert config.save_all_captures is False

    def test_custom_values(self, temp_output_dir: Path) -> None:
        """Test CaptureConfig with custom values."""
        config = CaptureConfig(
            output_directory=temp_output_dir,
            capture_interval_seconds=120,
            change_threshold=25,
            save_all_captures=True,
        )

        assert config.capture_interval_seconds == 120
        assert config.change_threshold == 25
        assert config.save_all_captures is True


class TestCaptureControllerErrorHandling:
    """Tests for error handling in CaptureController."""

    def test_capture_with_screenshot_error(  # noqa: PLR0917
        self,
        controller: CaptureController,
        mock_screenshot_capture: MagicMock,
        mock_image_processor: MagicMock,  # noqa: ARG002
        mock_change_detector: MagicMock,  # noqa: ARG002
        mock_focus_tracker: MagicMock,  # noqa: ARG002
        mock_window_enumerator: MagicMock,  # noqa: ARG002
        mock_date_directory_manager: MagicMock,  # noqa: ARG002
        mock_system_state_monitor: MagicMock,  # noqa: ARG002
    ) -> None:
        """Test error handling when screenshot capture fails."""
        mock_screenshot_capture.capture_all_monitors.side_effect = OSError(
            "Screenshot failed"
        )

        controller._perform_capture()

        assert controller.last_error_msg is not None
        assert "Screenshot failed" in controller.last_error_msg

    def test_capture_with_focus_error(  # noqa: PLR0917
        self,
        controller: CaptureController,
        mock_screenshot_capture: MagicMock,  # noqa: ARG002
        mock_image_processor: MagicMock,  # noqa: ARG002
        mock_change_detector: MagicMock,  # noqa: ARG002
        mock_focus_tracker: MagicMock,
        mock_window_enumerator: MagicMock,  # noqa: ARG002
        mock_date_directory_manager: MagicMock,  # noqa: ARG002
        mock_system_state_monitor: MagicMock,  # noqa: ARG002
    ) -> None:
        """Test error handling when focus tracking fails."""
        mock_focus_tracker.get_focused_application.side_effect = RuntimeError(
            "Focus error"
        )

        controller._perform_capture()

        assert controller.last_error_msg is not None
        assert "Focus error" in controller.last_error_msg
