from datetime import datetime
from pathlib import Path

from activity_beacon.logging import get_logger

logger = get_logger("activity_beacon.file_storage")


class DateDirectoryManager:
    """Manages date-based directory structures for organizing screenshots and data."""

    def __init__(self, base_path: Path | str) -> None:  # type: ignore[reportMissingSuperCall]
        """Initialize the directory manager with a base path.

        Args:
            base_path: The root directory where date-based subdirectories will be created.
        """
        self._base_path = Path(base_path).expanduser().resolve()
        self.last_error_msg: str | None = None
        logger.debug(
            f"Initialized DateDirectoryManager with base path: {self._base_path}"
        )

    def get_date_directory(self, date: datetime) -> Path:
        """Get the directory path for a specific date (YYYY/MM/DD structure).

        Args:
            date: The date for which to get the directory path.

        Returns:
            Path object representing the date-based directory.
        """
        year = date.strftime("%Y")
        month = date.strftime("%m")
        day = date.strftime("%d")
        return self._base_path / year / month / day

    def ensure_date_directory(self, date: datetime) -> Path:
        """Ensure the date directory exists, creating it if necessary.

        Args:
            date: The date for which to ensure the directory exists.

        Returns:
            Path object representing the created/existing directory.

        Raises:
            OSError: If directory creation fails due to permissions or other issues.
        """
        date_dir = self.get_date_directory(date)
        try:
            date_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {date_dir}")
            return date_dir
        except OSError as e:
            error_msg = f"Failed to create directory {date_dir}: {e}"
            logger.error(error_msg)
            raise OSError(error_msg) from e

    def get_screenshot_filename(self, timestamp: datetime) -> str:  # noqa: PLR6301
        """Generate a screenshot filename based on timestamp.

        Args:
            timestamp: The timestamp to use for the filename.

        Returns:
            Filename in format YYYYMMDD_HHMMSS.png
        """
        return timestamp.strftime("%Y%m%d_%H%M%S.png")

    def get_screenshot_path(self, timestamp: datetime) -> Path:
        """Get the full path for a screenshot file.

        Args:
            timestamp: The timestamp to use for the path and filename.

        Returns:
            Full path including directory and filename.
        """
        directory = self.get_date_directory(timestamp)
        filename = self.get_screenshot_filename(timestamp)
        return directory / filename

    def validate_path_security(self, path: Path) -> bool:
        """Validate that a path is within the base directory (prevent directory traversal).

        Args:
            path: The path to validate.

        Returns:
            True if path is safe and within base directory, False otherwise.
        """
        try:
            resolved_path = path.resolve()
            resolved_base = self._base_path.resolve()
            is_safe = resolved_path.is_relative_to(resolved_base)
            if not is_safe:
                logger.warning(
                    f"Path {path} is outside base directory {self._base_path}"
                )
            return is_safe
        except (ValueError, RuntimeError) as e:
            error_msg = f"Path validation failed for {path}: {e}"
            logger.warning(error_msg)
            self.last_error_msg = error_msg
            return False
