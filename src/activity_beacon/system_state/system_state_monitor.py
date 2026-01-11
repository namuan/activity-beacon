"""SystemStateMonitor for detecting screen lock state on macOS."""

from collections.abc import Callable
from typing import TYPE_CHECKING, cast

import Quartz  # type: ignore[import-untyped]

from activity_beacon.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = get_logger("activity_beacon.system_state")


class SystemStateMonitor:
    """Monitors macOS system state, particularly screen lock status.

    This class provides functionality to detect when the screen is locked,
    which can be used to pause screenshot capture and other activities.

    Notes:
        Uses Quartz.CGSessionCopyCurrentDictionary to check screen lock state.
        On macOS, when the screen is locked, the kCGSSessionScreenIsLocked
        key is set to 1; when unlocked, it's 0.
    """

    # Quartz key cached as class constant
    K_SCREEN_LOCKED = "CGSSessionScreenIsLocked"

    def __init__(self) -> None:  # type: ignore[no-untyped-def]
        """Initialize the SystemStateMonitor."""
        self.last_error_msg: str | None = None
        self._pause_callback: Callable[[], None] | None = None
        self._resume_callback: Callable[[], None] | None = None
        self._was_locked = False
        logger.debug("Initialized SystemStateMonitor")

    def set_callbacks(
        self,
        pause_func: Callable[[], None] | None = None,
        resume_callback: Callable[[], None] | None = None,
    ) -> None:
        """Set callbacks for pause/resume notifications.

        Args:
            pause_func: Function to call when screen is locked.
            resume_callback: Function to call when screen is unlocked.
        """
        self._pause_callback = pause_func
        self._resume_callback = resume_callback
        logger.debug(
            f"Set callbacks: pause={pause_func is not None}, resume={resume_callback is not None}"
        )

    def is_screen_locked(self) -> bool:
        """Check if the screen is currently locked.

        Returns:
            True if screen is locked, False otherwise.
        """
        try:
            session_info = cast(
                "Mapping[str, object] | None",
                Quartz.CGSessionCopyCurrentDictionary(),  # type: ignore[attr-defined]
            )  # type: ignore[no-untyped-call]
        except RuntimeError as exc:  # pragma: no cover - system API exceptions
            self.last_error_msg = str(exc)
            logger.error("Error reading session dictionary: %s", exc)
            return False

        if session_info is None:
            logger.warning("CGSessionCopyCurrentDictionary returned None")
            return False

        val = session_info.get(self.K_SCREEN_LOCKED, 0)
        if isinstance(val, int):
            return val == 1
        return False

    def check_and_notify(self) -> bool:
        """Check screen lock state and notify callbacks if changed.

        This method should be called periodically to detect screen lock
        state changes and trigger appropriate callbacks.

        Returns:
            True if screen is currently locked, False otherwise.
        """
        is_locked = self.is_screen_locked()

        if is_locked != self._was_locked:
            if is_locked:
                logger.info("Screen locked detected")
                if self._pause_callback:
                    self._pause_callback()
            else:
                logger.info("Screen unlocked detected")
                if self._resume_callback:
                    self._resume_callback()
            self._was_locked = is_locked

        return is_locked

    def get_state_description(self) -> str:
        """Get a human-readable description of the current state.

        Returns:
            String describing the current screen lock state.
        """
        return "locked" if self.is_screen_locked() else "unlocked"
