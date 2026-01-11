"""Tests for WindowEnumerator."""

from unittest.mock import patch

import pytest

from activity_beacon.window_tracking.window_enumerator import WindowEnumerator


@pytest.fixture
def mock_quartz():
    """Fixture to mock Quartz module."""
    with patch("activity_beacon.window_tracking.window_enumerator.Quartz") as mock:
        # Mock constants
        mock.kCGWindowListOptionOnScreenOnly = 1
        mock.kCGWindowListExcludeDesktopElements = 2
        mock.kCGNullWindowID = 0
        mock.kCGWindowLayer = "kCGWindowLayer"
        mock.kCGWindowOwnerName = "kCGWindowOwnerName"
        mock.kCGWindowName = "kCGWindowName"
        mock.kCGWindowOwnerPID = "kCGWindowOwnerPID"
        mock.kCGWindowBounds = "kCGWindowBounds"
        yield mock


def test_window_enumerator_initialization():
    """Test that WindowEnumerator can be initialized."""
    enumerator = WindowEnumerator()
    assert isinstance(enumerator, WindowEnumerator)


def test_enumerate_windows_empty(mock_quartz):
    """Test enumerate_windows when no windows are returned."""
    mock_quartz.CGWindowListCopyWindowInfo.return_value = []

    enumerator = WindowEnumerator()
    windows = enumerator.enumerate_windows()

    assert isinstance(windows, tuple)
    assert len(windows) == 0
    mock_quartz.CGWindowListCopyWindowInfo.assert_called_once()


def test_enumerate_windows_filtering(mock_quartz):
    """Test that windows are correctly filtered and mapped."""
    mock_windows = [
        {
            "kCGWindowLayer": 0,
            "kCGWindowOwnerName": "Finder",
            "kCGWindowName": "Desktop",
            "kCGWindowOwnerPID": 100,
            "kCGWindowBounds": {"X": 0, "Y": 0, "Width": 100, "Height": 100},
        },
        {
            "kCGWindowLayer": 1,  # Should be filtered out
            "kCGWindowOwnerName": "SystemUIServer",
            "kCGWindowName": "Menu",
            "kCGWindowOwnerPID": 101,
            "kCGWindowBounds": {"X": 50, "Y": 0, "Width": 200, "Height": 20},
        },
        {
            "kCGWindowLayer": 0,
            "kCGWindowOwnerName": "Terminal",
            "kCGWindowName": "bash",
            "kCGWindowOwnerPID": 102,
            "kCGWindowBounds": {"X": 10, "Y": 10, "Width": 500, "Height": 400},
        },
    ]
    mock_quartz.CGWindowListCopyWindowInfo.return_value = mock_windows

    enumerator = WindowEnumerator()
    windows = enumerator.enumerate_windows(focused_pid=102)

    assert len(windows) == 2

    # Check Finder window
    assert windows[0].app_name == "Finder"
    assert windows[0].window_name == "Desktop"
    assert windows[0].pid == 100
    assert windows[0].is_focused is False
    assert windows[0].screen_rect == (0, 0, 100, 100)

    # Check Terminal window
    assert windows[1].app_name == "Terminal"
    assert windows[1].window_name == "bash"
    assert windows[1].pid == 102
    assert windows[1].is_focused is True
    assert windows[1].screen_rect == (10, 10, 500, 400)


def test_enumerate_windows_missing_data(mock_quartz):
    """Test enumerate_windows with missing or malformed data."""
    mock_windows = [
        {
            "kCGWindowLayer": 0,
            # Missing owner name, window name, bounds
            "kCGWindowOwnerPID": 103,
        }
    ]
    mock_quartz.CGWindowListCopyWindowInfo.return_value = mock_windows

    enumerator = WindowEnumerator()
    windows = enumerator.enumerate_windows()

    assert len(windows) == 1
    assert windows[0].app_name == "Unknown"
    assert not windows[0].window_name
    assert windows[0].pid == 103
    assert windows[0].screen_rect == (0, 0, 0, 0)
