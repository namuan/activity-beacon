"""SystemStateMonitor for detecting screen lock status on macOS.

This module uses Quartz.CGSessionCopyCurrentDictionary to determine whether the
screen is currently locked and provides a listener-based notification API for
pause/resume events.
"""

from collections.abc import Callable
from contextlib import suppress
from typing import cast

import Quartz  # type: ignore[import-untyped]

from activity_beacon.logging import get_logger

logger = get_logger("activity_beacon.system")


class SystemStateMonitor:
    """Monitor macOS session state for screen lock/unlock events.

    Usage:
        monitor = SystemStateMonitor()
        monitor.add_listener(lambda locked: print("locked" if locked else "unlocked"))
        monitor.check_and_notify()
    """

    K_SCREEN_LOCKED = cast("str", Quartz.kCGSessionScreenIsLocked)  # type: ignore[attr-defined]

    def __init__(self) -> None:
        super().__init__()
        self.last_error_msg: str | None = None
        self._listeners: list[Callable[[bool], None]] = []
        self._last_state: bool | None = None

    def is_screen_locked(self) -> bool:
        """Return True if the session dictionary indicates the screen is locked.

        Returns False on error or when lock status cannot be determined.
        """
        try:
            session_dict = cast(
                "dict[str, object] | None", Quartz.CGSessionCopyCurrentDictionary()
            )  # type: ignore[no-untyped-call]
        except (
            RuntimeError,
            AttributeError,
        ) as exc:  # pragma: no cover - system API exceptions
            self.last_error_msg = str(exc)
            logger.error("Error reading session dictionary: %s", exc)
            return False

        if not session_dict:
            return False

        # Accessing the dictionary should be safe; any unexpected issues
        # will be treated as 'unlocked' and logged.
        val = session_dict.get(self.K_SCREEN_LOCKED, 0)
        if isinstance(val, int):
            return val == 1
        return False

    def add_listener(self, callback: Callable[[bool], None]) -> None:
        """Register a listener to be notified when lock state changes.

        The callback receives a single boolean parameter: True if the screen is
        locked, False otherwise.
        """
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[bool], None]) -> None:
        """Unregister a previously registered listener."""
        with suppress(ValueError):
            self._listeners.remove(callback)

    def check_and_notify(self) -> bool:
        """Check the current lock state and notify listeners on changes.

        On the very first invocation this method will set the internal state but
        will not notify listeners to avoid noisy startup notifications.

        Returns the current lock state.
        """
        current = self.is_screen_locked()

        # Initialize state without notifying on the first check
        if self._last_state is None:
            self._last_state = current
            return current

        if current == self._last_state:
            return current

        # State changed; notify listeners
        self._last_state = current
        for cb in list(self._listeners):
            try:
                cb(current)
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("Listener raised exception: %s", exc)

        return current
