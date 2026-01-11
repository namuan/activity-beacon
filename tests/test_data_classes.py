from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from activity_beacon.window_tracking.data import (
    FocusedAppData,
    WindowDataEntry,
    WindowInfo,
)


class TestWindowInfo:
    def test_window_info_creation(self) -> None:
        window_info = WindowInfo(
            window_name="Test Window",
            app_name="Test App",
            pid=12345,
            is_focused=True,
            screen_rect=(0, 0, 1920, 1080),
        )

        assert window_info.window_name == "Test Window"
        assert window_info.app_name == "Test App"
        assert window_info.pid == 12345
        assert window_info.is_focused is True
        assert window_info.screen_rect == (0, 0, 1920, 1080)

    def test_window_info_immutable(self) -> None:
        window_info = WindowInfo(
            window_name="Test",
            app_name="App",
            pid=1,
            is_focused=False,
            screen_rect=(0, 0, 100, 100),
        )

        with pytest.raises(FrozenInstanceError):
            window_info.window_name = "Changed"  # type: ignore[misc]


class TestFocusedAppData:
    def test_focused_app_data_creation(self) -> None:
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        data = FocusedAppData(
            app_name="Safari",
            pid=12345,
            window_name="Home - Safari",
            timestamp=timestamp,
        )

        assert data.app_name == "Safari"
        assert data.pid == 12345
        assert data.window_name == "Home - Safari"
        assert data.timestamp == timestamp

    def test_focused_app_data_with_null_window(self) -> None:
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        data = FocusedAppData(
            app_name="Finder",
            pid=123,
            window_name=None,
            timestamp=timestamp,
        )

        assert data.window_name is None


class TestWindowDataEntry:
    def test_window_data_entry_creation(
        self, sample_focused_app_data: FocusedAppData, sample_window_info: WindowInfo
    ) -> None:
        entry = WindowDataEntry(
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            focused_app=sample_focused_app_data,
            all_windows=(sample_window_info,),
            screenshot_path="/path/to/screenshot.png",
        )

        assert entry.timestamp == datetime(2024, 1, 15, 10, 30, 0)
        assert entry.focused_app == sample_focused_app_data
        assert len(entry.all_windows) == 1
        assert entry.screenshot_path == "/path/to/screenshot.png"

    def test_window_data_entry_with_multiple_windows(
        self, sample_focused_app_data: FocusedAppData
    ) -> None:
        window1 = WindowInfo(
            window_name="Window 1",
            app_name="App1",
            pid=1,
            is_focused=True,
            screen_rect=(0, 0, 100, 100),
        )
        window2 = WindowInfo(
            window_name="Window 2",
            app_name="App2",
            pid=2,
            is_focused=False,
            screen_rect=(100, 0, 200, 100),
        )

        entry = WindowDataEntry(
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            focused_app=sample_focused_app_data,
            all_windows=(window1, window2),
            screenshot_path=None,
        )

        assert len(entry.all_windows) == 2
        assert entry.screenshot_path is None

    def test_window_data_entry_immutable(
        self, sample_focused_app_data: FocusedAppData, sample_window_info: WindowInfo
    ) -> None:
        entry = WindowDataEntry(
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            focused_app=sample_focused_app_data,
            all_windows=(sample_window_info,),
            screenshot_path=None,
        )

        with pytest.raises(FrozenInstanceError):
            entry.timestamp = datetime(2024, 1, 15, 11, 0, 0)  # type: ignore[misc]
