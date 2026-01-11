from contextlib import ExitStack
from dataclasses import FrozenInstanceError
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from PIL import Image
import pytest

from activity_beacon.screenshot.capture import MonitorInfo, ScreenshotCapture


class TestMonitorInfo:
    def test_monitor_info_creation(self) -> None:
        monitor_info = MonitorInfo(
            monitor_id=1,
            name="Monitor 1",
            x=0,
            y=0,
            width=1920,
            height=1080,
            is_primary=True,
        )

        assert monitor_info.monitor_id == 1
        assert monitor_info.name == "Monitor 1"
        assert monitor_info.x == 0
        assert monitor_info.y == 0
        assert monitor_info.width == 1920
        assert monitor_info.height == 1080
        assert monitor_info.is_primary is True

    def test_monitor_info_geometry(self) -> None:
        monitor_info = MonitorInfo(
            monitor_id=1,
            name="Monitor 1",
            x=100,
            y=200,
            width=1920,
            height=1080,
            is_primary=False,
        )

        assert monitor_info.geometry == (100, 200, 1920, 1080)

    def test_monitor_info_resolution(self) -> None:
        monitor_info = MonitorInfo(
            monitor_id=1,
            name="Monitor 1",
            x=0,
            y=0,
            width=2560,
            height=1440,
            is_primary=True,
        )

        assert monitor_info.resolution == (2560, 1440)

    def test_monitor_info_immutable(self) -> None:
        monitor_info = MonitorInfo(
            monitor_id=1,
            name="Monitor 1",
            x=0,
            y=0,
            width=1920,
            height=1080,
            is_primary=True,
        )

        with pytest.raises(FrozenInstanceError):
            monitor_info.width = 2048  # type: ignore[misc]


class TestScreenshotCapture:
    def test_enumerate_monitors(self) -> None:
        with patch("mss.mss") as mock_mss:
            mock_sct = MagicMock()
            mock_sct.monitors = [
                {"left": 0, "top": 0, "width": 3720, "height": 1169},
                {"left": 0, "top": 0, "width": 1800, "height": 1169},
                {"left": 1800, "top": 89, "width": 1920, "height": 1080},
            ]
            mock_mss.return_value = mock_sct

            capture = ScreenshotCapture()
            monitors = capture.enumerate_monitors()

            assert len(monitors) == 2
            assert monitors[0].monitor_id == 1
            assert monitors[0].is_primary is True
            assert monitors[0].width == 1800
            assert monitors[0].height == 1169
            assert monitors[1].monitor_id == 2
            assert monitors[1].is_primary is False
            assert monitors[1].x == 1800
            assert monitors[1].y == 89

    def test_get_monitor_count(self) -> None:
        with patch("mss.mss") as mock_mss:
            mock_sct = MagicMock()
            mock_sct.monitors = [
                {"left": 0, "top": 0, "width": 1920, "height": 1080},
                {"left": 0, "top": 0, "width": 1920, "height": 1080},
            ]
            mock_mss.return_value = mock_sct

            capture = ScreenshotCapture()
            count = capture.get_monitor_count()

            assert count == 1

    def test_get_monitor_info(self) -> None:
        with patch("mss.mss") as mock_mss:
            mock_sct = MagicMock()
            mock_sct.monitors = [
                {"left": 0, "top": 0, "width": 4480, "height": 1080},
                {"left": 0, "top": 0, "width": 1920, "height": 1080},
                {"left": 1920, "top": 0, "width": 2560, "height": 1440},
            ]
            mock_mss.return_value = mock_sct

            capture = ScreenshotCapture()
            monitor = capture.get_monitor_info(1)

            assert monitor is not None
            assert monitor.monitor_id == 1
            assert monitor.width == 1920
            assert monitor.height == 1080

    def test_get_monitor_info_not_found(self) -> None:
        with patch("mss.mss") as mock_mss:
            mock_sct = MagicMock()
            mock_sct.monitors = [
                {"left": 0, "top": 0, "width": 1920, "height": 1080},
                {"left": 1920, "top": 0, "width": 2560, "height": 1440},
            ]
            mock_mss.return_value = mock_sct

            capture = ScreenshotCapture()
            monitor = capture.get_monitor_info(99)

            assert monitor is None

    def test_capture_monitor(self) -> None:
        with patch("mss.mss") as mock_mss:
            mock_sct = MagicMock()
            mock_sct.monitors = [
                {"left": 0, "top": 0, "width": 1920, "height": 1080},
                {"left": 0, "top": 0, "width": 1920, "height": 1080},
            ]
            mock_mss.return_value = mock_sct

            mock_image = MagicMock(spec=Image.Image)
            mock_sct_img = MagicMock()
            mock_sct_img.size = (1920, 1080)
            mock_sct_img.bgra = b"RGB" * 1920 * 1080
            mock_sct.grab.return_value = mock_sct_img

            with patch(
                "activity_beacon.screenshot.capture.Image.frombytes"
            ) as mock_frombytes:
                mock_frombytes.return_value = mock_image

                capture = ScreenshotCapture()
                image = capture.capture_monitor(1)

                assert image == mock_image
                mock_sct.grab.assert_called_once_with({
                    "left": 0,
                    "top": 0,
                    "width": 1920,
                    "height": 1080,
                })

    def test_capture_monitor_not_found(self) -> None:
        with patch("mss.mss") as mock_mss:
            mock_sct = MagicMock()
            mock_sct.monitors = [
                {"left": 0, "top": 0, "width": 1920, "height": 1080},
                {"left": 0, "top": 0, "width": 1920, "height": 1080},
            ]
            mock_mss.return_value = mock_sct

            capture = ScreenshotCapture()

            with pytest.raises(ValueError, match="Monitor 99 not found"):
                capture.capture_monitor(99)

    def test_capture_to_path(self) -> None:
        with ExitStack() as stack:
            tmpdir = stack.enter_context(TemporaryDirectory())
            mock_mss = stack.enter_context(patch("mss.mss"))
            mock_frombytes = stack.enter_context(
                patch("activity_beacon.screenshot.capture.Image.frombytes")
            )

            mock_sct = MagicMock()
            mock_sct.monitors = [
                {"left": 0, "top": 0, "width": 1920, "height": 1080},
                {"left": 0, "top": 0, "width": 1920, "height": 1080},
            ]
            mock_mss.return_value = mock_sct

            mock_image = MagicMock(spec=Image.Image)
            mock_sct_img = MagicMock()
            mock_sct_img.size = (1920, 1080)
            mock_sct_img.bgra = b"RGB" * 1920 * 1080
            mock_sct.grab.return_value = mock_sct_img

            mock_frombytes.return_value = mock_image

            capture = ScreenshotCapture()
            output_path = capture.capture_to_path(
                1, Path(tmpdir) / "test.png", format="PNG"
            )

            mock_image.save.assert_called_once()
            assert output_path.parent.exists()

    def test_context_manager(self) -> None:
        with patch("mss.mss") as mock_mss:
            mock_sct = MagicMock()
            mock_sct.monitors = [
                {"left": 0, "top": 0, "width": 1920, "height": 1080},
                {"left": 0, "top": 0, "width": 1920, "height": 1080},
            ]
            mock_mss.return_value = mock_sct

            with ScreenshotCapture() as capture:
                count = capture.get_monitor_count()
                assert count == 1

            mock_sct.close.assert_called_once()

    def test_close(self) -> None:
        with patch("mss.mss") as mock_mss:
            mock_sct = MagicMock()
            mock_sct.monitors = [
                {"left": 0, "top": 0, "width": 1920, "height": 1080},
                {"left": 0, "top": 0, "width": 1920, "height": 1080},
            ]
            mock_mss.return_value = mock_sct

            capture = ScreenshotCapture()
            capture.enumerate_monitors()
            capture.close()

            mock_sct.close.assert_called_once()
            assert capture._mss is None

    def test_capture_all_monitors(self) -> None:
        with patch("mss.mss") as mock_mss:
            mock_sct = MagicMock()
            mock_sct.monitors = [
                {"left": 0, "top": 0, "width": 1920, "height": 1080},
                {"left": 0, "top": 0, "width": 1920, "height": 1080},
                {"left": 1920, "top": 0, "width": 2560, "height": 1440},
            ]
            mock_mss.return_value = mock_sct

            mock_image = MagicMock(spec=Image.Image)
            mock_sct_img = MagicMock()
            mock_sct_img.size = (1920, 1080)
            mock_sct_img.bgra = b"RGB" * 1920 * 1080
            mock_sct.grab.return_value = mock_sct_img

            with patch(
                "activity_beacon.screenshot.capture.Image.frombytes"
            ) as mock_frombytes:
                mock_frombytes.return_value = mock_image

                capture = ScreenshotCapture()
                captures = capture.capture_all_monitors()

                assert len(captures) == 2
                assert 1 in captures
                assert 2 in captures
