"""FocusTracker for detecting active application and focused window using macOS APIs."""

from datetime import UTC, datetime
from typing import cast

from AppKit import NSWorkspace  # type: ignore[import-untyped]

from activity_beacon.logging import get_logger
from activity_beacon.window_tracking.data import FocusedAppData

logger = get_logger("activity_beacon.window_tracking")


class FocusTracker:
    """Tracks the active application and its focused window using AppKit.NSWorkspace.

    This class provides functionality to detect which application is currently active
    and extract information about its focused window, including the application name,
    process ID, and window name.
    """

    def __init__(self) -> None:
        """Initialize the FocusTracker with NSWorkspace."""
        super().__init__()
        self.workspace = NSWorkspace.sharedWorkspace()  # type: ignore[no-untyped-call]
        self.last_error_msg: str | None = None

    def get_focused_application(self) -> FocusedAppData:
        """Get information about the currently focused application.

        Returns:
            FocusedAppData: Object containing the active application's name, PID,
                window name (if available), and timestamp.

        Notes:
            - If the active application cannot be determined, returns placeholder values
            - Window name may be None if not available or accessible
            - Timestamp is always in UTC timezone
        """
        try:
            active_app = self.workspace.frontmostApplication()  # type: ignore[no-untyped-call]

            if not active_app:
                # Return placeholder if no active application
                return FocusedAppData(
                    app_name="Unknown",
                    pid=0,
                    window_name=None,
                    timestamp=datetime.now(UTC),
                )

            app_name = cast("str", active_app.localizedName() or "Unknown")  # type: ignore[no-untyped-call]
            pid = cast("int", active_app.processIdentifier())  # type: ignore[no-untyped-call]

            # Try to get window name from the active application
            # Note: NSWorkspace doesn't directly provide window names,
            # so this may return None for many applications
            window_name = self._get_window_name()

            return FocusedAppData(
                app_name=app_name,
                pid=pid,
                window_name=window_name,
                timestamp=datetime.now(UTC),
            )

        except RuntimeError as e:
            error_msg = f"Failed to get focused application: {e}"
            logger.error(error_msg)
            self.last_error_msg = error_msg
            return FocusedAppData(
                app_name="Unknown",
                pid=0,
                window_name=None,
                timestamp=datetime.now(UTC),
            )

    @staticmethod
    def _get_window_name() -> str | None:
        """Extract window name from the active application.

        Returns:
            Window name if available, None otherwise

        Notes:
            NSWorkspace API has limited access to window titles. This is a
            best-effort implementation and may return None for most applications.
            For complete window information, WindowEnumerator should be used instead.
        """
        # NSWorkspace doesn't provide direct access to window titles
        # This would require more advanced techniques using Accessibility API
        # or Quartz Window Services (which will be in WindowEnumerator)
        # For now, return None to indicate window name is not available via this API
        return None
