from collections.abc import Generator
from datetime import datetime
from pathlib import Path

import pytest

from activity_beacon.window_tracking.data import (
    FocusedAppData,
    WindowDataEntry,
    WindowInfo,
)


@pytest.fixture
def temp_log_dir(tmp_path: Path) -> Generator[Path, None, None]:
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    yield log_dir


@pytest.fixture
def sample_window_info() -> WindowInfo:
    return WindowInfo(
        window_name="Test Window",
        app_name="Test App",
        pid=12345,
        is_focused=True,
        screen_rect=(0, 0, 1920, 1080),
    )


@pytest.fixture
def sample_focused_app_data() -> FocusedAppData:
    return FocusedAppData(
        app_name="Safari",
        pid=12345,
        window_name="Test Page - Safari",
        timestamp=datetime(2024, 1, 15, 10, 30, 0),
    )


@pytest.fixture
def sample_window_data_entry(
    sample_focused_app_data: FocusedAppData, sample_window_info: WindowInfo
) -> WindowDataEntry:
    return WindowDataEntry(
        timestamp=datetime(2024, 1, 15, 10, 30, 0),
        focused_app=sample_focused_app_data,
        all_windows=(sample_window_info,),
        screenshot_path="/path/to/screenshot.png",
    )


@pytest.fixture
def mock_screenshot_dir(tmp_path: Path) -> Generator[Path, None, None]:
    year_dir = tmp_path / "2024" / "01" / "15"
    year_dir.mkdir(parents=True)
    yield tmp_path
