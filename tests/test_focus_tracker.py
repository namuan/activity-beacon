"""Tests for FocusTracker class."""

from datetime import UTC, datetime

import pytest

from activity_beacon.window_tracking.data import FocusedAppData
from activity_beacon.window_tracking.focus_tracker import FocusTracker


class TestFocusTracker:
    """Test suite for FocusTracker class."""

    @pytest.fixture
    def tracker(self) -> FocusTracker:
        """Create a FocusTracker instance for testing."""
        return FocusTracker()

    def test_init(self, tracker: FocusTracker) -> None:
        """Test that FocusTracker initializes correctly."""
        assert tracker is not None
        assert tracker.workspace is not None

    def test_get_focused_application_returns_focused_app_data(
        self, tracker: FocusTracker
    ) -> None:
        """Test that get_focused_application returns FocusedAppData."""
        result = tracker.get_focused_application()

        assert isinstance(result, FocusedAppData)
        assert isinstance(result.app_name, str)
        assert isinstance(result.pid, int)
        assert result.window_name is None or isinstance(result.window_name, str)
        assert isinstance(result.timestamp, datetime)

    def test_get_focused_application_has_valid_app_name(
        self, tracker: FocusTracker
    ) -> None:
        """Test that the returned app name is not empty."""
        result = tracker.get_focused_application()

        # Should have some app name (at minimum "Unknown" or the test runner)
        assert result.app_name
        assert len(result.app_name) > 0

    def test_get_focused_application_has_valid_pid(self, tracker: FocusTracker) -> None:
        """Test that the returned PID is valid."""
        result = tracker.get_focused_application()

        # PID should be non-negative
        assert result.pid >= 0

    def test_get_focused_application_timestamp_is_utc(
        self, tracker: FocusTracker
    ) -> None:
        """Test that timestamp is in UTC timezone."""
        result = tracker.get_focused_application()

        assert result.timestamp.tzinfo is not None
        assert result.timestamp.tzinfo == UTC

    def test_get_focused_application_timestamp_is_recent(
        self, tracker: FocusTracker
    ) -> None:
        """Test that timestamp is close to current time."""
        before = datetime.now(UTC)
        result = tracker.get_focused_application()
        after = datetime.now(UTC)

        # Timestamp should be between before and after
        assert before <= result.timestamp <= after

    def test_get_focused_application_consistency(self, tracker: FocusTracker) -> None:
        """Test that consecutive calls return consistent data."""
        result1 = tracker.get_focused_application()
        result2 = tracker.get_focused_application()

        # App name and PID should be the same for consecutive calls
        # (assuming no app switching happened)
        assert result1.app_name == result2.app_name
        assert result1.pid == result2.pid

    def test_window_name_handling(self, tracker: FocusTracker) -> None:
        """Test that window name is None (as expected from NSWorkspace limitations)."""
        result = tracker.get_focused_application()

        # NSWorkspace doesn't provide window names, so it should be None
        assert result.window_name is None
