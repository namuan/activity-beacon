"""WindowEnumerator for collecting information about all visible windows on macOS."""

from typing import TYPE_CHECKING, cast

import Quartz  # type: ignore[import-untyped]

from activity_beacon.logging import get_logger
from activity_beacon.window_tracking.data import WindowInfo

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = get_logger("activity_beacon.window_tracking")


class WindowEnumerator:
    """Enumerates all visible windows using Quartz Window Services.

    This class provides functionality to collect metadata about all windows
    currently visible on the screen, including their titles, owner applications,
    process IDs, and geometry.
    """

    # Quartz keys cached as class constants to avoid repeated casting and reduce local variables
    # We use cast and type: ignore to handle missing type stubs for Quartz
    K_LAYER = cast("str", Quartz.kCGWindowLayer)  # type: ignore[attr-defined]
    K_OWNER_NAME = cast("str", Quartz.kCGWindowOwnerName)  # type: ignore[attr-defined]
    K_NAME = cast("str", Quartz.kCGWindowName)  # type: ignore[attr-defined]
    K_OWNER_PID = cast("str", Quartz.kCGWindowOwnerPID)  # type: ignore[attr-defined]
    K_BOUNDS = cast("str", Quartz.kCGWindowBounds)  # type: ignore[attr-defined]

    def __init__(self) -> None:
        """Initialize the WindowEnumerator."""
        super().__init__()
        self.last_error_msg: str | None = None

    def enumerate_windows(
        self, focused_pid: int | None = None
    ) -> tuple[WindowInfo, ...]:
        """Collect information about all visible windows.

        Args:
            focused_pid: Optional PID of the currently focused application to
                mark windows as focused.

        Returns:
            tuple[WindowInfo, ...]: A tuple of WindowInfo objects for each visible window.
        """
        try:
            # Options for window list: on-screen only, exclude desktop elements
            # PyObjC constants are often not recognized by static analyzers
            k_on_screen = cast("int", Quartz.kCGWindowListOptionOnScreenOnly)  # type: ignore[attr-defined]
            k_exclude_desktop = cast("int", Quartz.kCGWindowListExcludeDesktopElements)  # type: ignore[attr-defined]
            k_null_id = cast("int", Quartz.kCGNullWindowID)  # type: ignore[attr-defined]

            list_options = k_on_screen | k_exclude_desktop

            # Get the window list information
            # Using cast to Mapping for basedpyright
            window_list = cast(
                "list[Mapping[str, object]]",
                Quartz.CGWindowListCopyWindowInfo(list_options, k_null_id),
            )  # type: ignore[no-untyped-call]

            if not window_list:
                return ()

            windows: list[WindowInfo] = []
            for window_data in window_list:
                # Skip windows with layer > 0 (usually system overlays, menus, etc.)
                layer = cast("int", window_data.get(self.K_LAYER, 0))
                if layer != 0:
                    continue

                windows.append(self._parse_window_data(window_data, focused_pid))

            return tuple(windows)

        except RuntimeError as e:
            error_msg = f"Failed to enumerate windows: {e}"
            logger.error(error_msg)
            self.last_error_msg = error_msg
            return ()

    def _parse_window_data(
        self,
        window_data: "Mapping[str, object]",
        focused_pid: int | None,
    ) -> WindowInfo:
        """Parse individual window data dictionary into WindowInfo.

        Args:
            window_data: Raw window data from Quartz.
            focused_pid: PID of the focused application.

        Returns:
            WindowInfo: Structured window information.
        """
        app_name = cast("str", window_data.get(self.K_OWNER_NAME, "Unknown"))
        window_name = cast("str", window_data.get(self.K_NAME, ""))
        pid = cast("int", window_data.get(self.K_OWNER_PID, 0))

        # Extract window bounds (geometry)
        bounds = cast("Mapping[str, float] | None", window_data.get(self.K_BOUNDS))
        if bounds:
            rect = (
                int(bounds.get("X", 0.0)),
                int(bounds.get("Y", 0.0)),
                int(bounds.get("Width", 0.0)),
                int(bounds.get("Height", 0.0)),
            )
        else:
            rect = (0, 0, 0, 0)

        return WindowInfo(
            window_name=window_name,
            app_name=app_name,
            pid=pid,
            is_focused=focused_pid is not None and pid == focused_pid,
            screen_rect=rect,
        )
