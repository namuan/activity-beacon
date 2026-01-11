"""Tests for error handling across components."""

from contextlib import suppress
from datetime import datetime
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch

from PIL import Image
import pytest

from activity_beacon.file_storage.date_directory_manager import DateDirectoryManager
from activity_beacon.file_storage.jsonl_writer import JSONLWriter
from activity_beacon.screenshot.capture import ScreenshotCapture
from activity_beacon.screenshot.change_detector import ChangeDetector
from activity_beacon.screenshot.image_processor import ImageProcessor
from activity_beacon.system_state.system_state_monitor import SystemStateMonitor
from activity_beacon.window_tracking.focus_tracker import FocusTracker
from activity_beacon.window_tracking.window_enumerator import WindowEnumerator


class TestErrorHandlingProperties:
    """Test that all components have last_error_msg property."""

    def test_screenshot_capture_has_last_error_msg(self) -> None:
        """Test ScreenshotCapture has last_error_msg property."""
        capture = ScreenshotCapture()
        assert hasattr(capture, "last_error_msg")
        assert capture.last_error_msg is None

    def test_image_processor_has_last_error_msg(self) -> None:
        """Test ImageProcessor has last_error_msg property."""
        processor = ImageProcessor()
        assert hasattr(processor, "last_error_msg")
        assert processor.last_error_msg is None

    def test_change_detector_has_last_error_msg(self) -> None:
        """Test ChangeDetector has last_error_msg property."""
        detector = ChangeDetector()
        assert hasattr(detector, "last_error_msg")
        assert detector.last_error_msg is None

    def test_date_directory_manager_has_last_error_msg(self) -> None:
        """Test DateDirectoryManager has last_error_msg property."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DateDirectoryManager(tmpdir)
            assert hasattr(manager, "last_error_msg")
            assert manager.last_error_msg is None

    def test_jsonl_writer_has_last_error_msg(self) -> None:
        """Test JSONLWriter has last_error_msg property."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = JSONLWriter(Path(tmpdir) / "test.jsonl")
            assert hasattr(writer, "last_error_msg")
            assert writer.last_error_msg is None

    def test_system_state_monitor_has_last_error_msg(self) -> None:
        """Test SystemStateMonitor has last_error_msg property."""
        monitor = SystemStateMonitor()
        assert hasattr(monitor, "last_error_msg")
        assert monitor.last_error_msg is None

    def test_focus_tracker_has_last_error_msg(self) -> None:
        """Test FocusTracker has last_error_msg property."""
        tracker = FocusTracker()
        assert hasattr(tracker, "last_error_msg")
        assert tracker.last_error_msg is None

    def test_window_enumerator_has_last_error_msg(self) -> None:
        """Test WindowEnumerator has last_error_msg property."""
        enumerator = WindowEnumerator()
        assert hasattr(enumerator, "last_error_msg")
        assert enumerator.last_error_msg is None


class TestScreenshotCaptureErrorHandling:
    """Test error handling in ScreenshotCapture."""

    def _create_mock_capture(self, capture: ScreenshotCapture) -> Image.Image:
        """Set up mock for capture_monitor method."""
        mock_image = Image.new("RGB", (100, 100), (255, 0, 0))
        with patch.object(capture, "capture_monitor", return_value=mock_image):
            return mock_image

    def test_permission_error_wrapping(self) -> None:
        """Test that PermissionError is wrapped with descriptive message."""
        capture = ScreenshotCapture()
        self._create_mock_capture(capture)

        with tempfile.TemporaryDirectory() as tmpdir:
            protected_path = Path(tmpdir) / "subdir" / "test.png"
            with patch.object(
                Path, "mkdir", side_effect=PermissionError("Permission denied")
            ):
                with pytest.raises(OSError, match="Permission denied writing to"):
                    capture.capture_to_path(1, protected_path)

                assert capture.last_error_msg is not None
                assert "Permission denied" in capture.last_error_msg

    def test_os_error_wrapping(self) -> None:
        """Test that OSError is wrapped with descriptive message."""
        capture = ScreenshotCapture()
        self._create_mock_capture(capture)

        with tempfile.TemporaryDirectory() as tmpdir:
            protected_path = Path(tmpdir) / "subdir" / "test.png"
            with patch.object(Path, "mkdir", side_effect=OSError("Disk full")):
                with pytest.raises(OSError, match="Failed to write screenshot"):
                    capture.capture_to_path(1, protected_path)

                assert capture.last_error_msg is not None
                assert "Disk full" in capture.last_error_msg

    def test_last_error_msg_cleared_on_success(self) -> None:
        """Test that last_error_msg is cleared on successful operation."""
        capture = ScreenshotCapture()
        # First, cause an error
        with tempfile.TemporaryDirectory() as tmpdir:
            protected_path = Path(tmpdir) / "subdir" / "test.png"
            with (
                patch.object(
                    Path, "mkdir", side_effect=PermissionError("Permission denied")
                ),
                suppress(OSError),
            ):
                capture.capture_to_path(1, protected_path)

            assert capture.last_error_msg is not None

        # Now do a successful operation
        capture2 = ScreenshotCapture()  # Create a new instance to avoid state
        with tempfile.TemporaryDirectory() as tmpdir2:
            valid_path = Path(tmpdir2) / "test.png"
            capture2.capture_to_path(1, valid_path)

            # last_error_msg should be cleared after success
            assert capture2.last_error_msg is None


class TestDateDirectoryManagerErrorHandling:
    """Test error handling in DateDirectoryManager."""

    def test_path_validation_error_message(self) -> None:
        """Test that path validation errors are captured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DateDirectoryManager(tmpdir)

            # Test with an invalid path that raises ValueError
            mock_path = MagicMock()
            mock_path.resolve.side_effect = ValueError("Invalid path")

            result = manager.validate_path_security(mock_path)

            assert result is False
            assert manager.last_error_msg is not None
            assert "Path validation failed" in manager.last_error_msg

    def test_ensure_date_directory_error_message(self) -> None:
        """Test that directory creation errors are wrapped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DateDirectoryManager(tmpdir)
            date = datetime.now()

            # Mock mkdir to raise OSError
            with (
                patch.object(
                    Path, "mkdir", side_effect=OSError("Read-only filesystem")
                ),
                pytest.raises(OSError, match="Failed to create directory"),
            ):
                manager.ensure_date_directory(date)


class TestJSONLWriterErrorHandling:
    """Test error handling in JSONLWriter."""

    def test_parent_mkdir_permission_error(self) -> None:
        """Test that parent directory creation permission errors are handled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a subdirectory that we don't have write access to
            protected_subdir = Path(tmpdir) / "protected"
            protected_subdir.mkdir(mode=0o000)
            try:
                writer = JSONLWriter(protected_subdir / "test.jsonl")

                with pytest.raises(OSError):
                    writer.write({"test": "data"})

                assert writer.last_error_msg is not None
            finally:
                # Restore permissions for cleanup
                protected_subdir.chmod(0o755)


class TestFocusTrackerErrorHandling:
    """Test error handling in FocusTracker."""

    def test_last_error_msg_is_none_on_success(self) -> None:
        """Test that last_error_msg is None after successful operation."""
        tracker = FocusTracker()
        result = tracker.get_focused_application()

        # Should return valid data without error
        assert result.app_name is not None
        assert result.pid >= 0
        assert tracker.last_error_msg is None


class TestWindowEnumeratorErrorHandling:
    """Test error handling in WindowEnumerator."""

    def test_runtime_error_handling(self) -> None:
        """Test that RuntimeError from Quartz is handled gracefully."""
        enumerator = WindowEnumerator()

        # Mock CGWindowListCopyWindowInfo to raise RuntimeError
        with patch(
            "activity_beacon.window_tracking.window_enumerator.Quartz.CGWindowListCopyWindowInfo",
            side_effect=RuntimeError("Quartz error"),
        ):
            result = enumerator.enumerate_windows()

            # Should return empty tuple
            assert result == ()
            assert enumerator.last_error_msg is not None
            assert "Failed to enumerate windows" in enumerator.last_error_msg


class TestImageProcessorErrorHandling:
    """Test error handling in ImageProcessor."""

    def test_empty_images_error_message(self) -> None:
        """Test that empty image collection error is captured."""
        processor = ImageProcessor()

        with pytest.raises(ValueError, match="Cannot stitch empty image collection"):
            processor.stitch_horizontally({})

        assert processor.last_error_msg is not None
        assert "Cannot stitch empty image collection" in processor.last_error_msg


class TestSystemStateMonitorErrorHandling:
    """Test error handling in SystemStateMonitor."""

    def test_runtime_error_handling(self) -> None:
        """Test that RuntimeError from CGSessionCopyCurrentDictionary is handled."""
        monitor = SystemStateMonitor()

        # Mock CGSessionCopyCurrentDictionary to raise RuntimeError
        with patch(
            "activity_beacon.system_state.system_state_monitor.Quartz.CGSessionCopyCurrentDictionary",
            side_effect=RuntimeError("Session error"),
        ):
            result = monitor.is_screen_locked()

            # Should return False on error
            assert result is False
            assert monitor.last_error_msg is not None
