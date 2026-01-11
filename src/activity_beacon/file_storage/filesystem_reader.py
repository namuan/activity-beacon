from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re

from activity_beacon.logging import get_logger

logger = get_logger("activity_beacon.file_storage")


@dataclass(frozen=True)
class ValidationReport:
    """Report of directory structure validation."""

    is_valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    found_screenshots: tuple[str, ...]
    found_data_files: tuple[str, ...]


class FileSystemReader:
    """Validates captured data directory structure."""

    # Expected filename patterns
    SCREENSHOT_PATTERN = re.compile(r"^\d{8}_\d{6}\.png$")
    WINDOW_DATA_FILENAME = "window_data.jsonl"

    def __init__(self, base_path: Path | str) -> None:  # type: ignore[reportMissingSuperCall]
        """Initialize the filesystem reader with a base path.

        Args:
            base_path: The root directory to validate.
        """
        self._base_path = Path(base_path).expanduser().resolve()
        self.last_error_msg: str | None = None
        logger.debug(f"Initialized FileSystemReader with base path: {self._base_path}")

    def validate_date_directory(  # noqa: C901, PLR0912
        self, date: datetime
    ) -> ValidationReport:
        """Validate the directory structure for a specific date.

        Args:
            date: The date to validate.

        Returns:
            ValidationReport with validation results.
        """
        errors: list[str] = []
        warnings: list[str] = []
        screenshots: list[str] = []
        data_files: list[str] = []

        # Build expected directory path
        year = date.strftime("%Y")
        month = date.strftime("%m")
        day = date.strftime("%d")
        date_dir = self._base_path / year / month / day

        # Check if directory exists
        if not date_dir.exists():
            errors.append(f"Date directory does not exist: {date_dir}")
            return ValidationReport(
                is_valid=False,
                errors=tuple(errors),
                warnings=tuple(warnings),
                found_screenshots=tuple(screenshots),
                found_data_files=tuple(data_files),
            )

        if not date_dir.is_dir():
            errors.append(f"Path exists but is not a directory: {date_dir}")
            return ValidationReport(
                is_valid=False,
                errors=tuple(errors),
                warnings=tuple(warnings),
                found_screenshots=tuple(screenshots),
                found_data_files=tuple(data_files),
            )

        # Validate directory structure (YYYY/MM/DD)
        if not self._validate_directory_structure(date_dir, year, month, day):
            errors.append(
                f"Invalid directory structure: expected YYYY/MM/DD format, got {date_dir}"
            )

        # Check for window data file
        window_data_path = date_dir / self.WINDOW_DATA_FILENAME
        if window_data_path.exists():
            if window_data_path.is_file():
                data_files.append(self.WINDOW_DATA_FILENAME)
            else:
                errors.append(
                    f"Window data path exists but is not a file: {window_data_path}"
                )
        else:
            warnings.append(f"No window data file found: {self.WINDOW_DATA_FILENAME}")

        # Check for screenshot files
        try:
            for item in date_dir.iterdir():
                if item.is_file() and self._is_valid_screenshot_name(item.name):
                    screenshots.append(item.name)
                elif item.is_file() and item.name.endswith(".png"):
                    warnings.append(
                        f"PNG file with invalid naming convention: {item.name}"
                    )
        except PermissionError as e:
            error_msg = f"Permission denied reading directory {date_dir}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            self.last_error_msg = error_msg
        except OSError as e:
            error_msg = f"Failed to read directory {date_dir}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            self.last_error_msg = error_msg

        # Check if we have any screenshots
        if not screenshots:
            warnings.append("No valid screenshot files found")

        is_valid = len(errors) == 0

        return ValidationReport(
            is_valid=is_valid,
            errors=tuple(errors),
            warnings=tuple(warnings),
            found_screenshots=tuple(screenshots),
            found_data_files=tuple(data_files),
        )

    def _validate_directory_structure(  # noqa: PLR6301
        self, date_dir: Path, year: str, month: str, day: str
    ) -> bool:
        """Validate that directory follows YYYY/MM/DD structure.

        Args:
            date_dir: The directory to validate.
            year: Expected year (YYYY).
            month: Expected month (MM).
            day: Expected day (DD).

        Returns:
            True if structure is valid, False otherwise.
        """
        # Check if the path components match expected structure
        min_path_components = 3
        parts = date_dir.parts
        if len(parts) < min_path_components:
            return False

        # Get last 3 parts (day/month/year from the end)
        actual_day = parts[-1]
        actual_month = parts[-2]
        actual_year = parts[-3]

        return actual_year == year and actual_month == month and actual_day == day

    def _is_valid_screenshot_name(self, filename: str) -> bool:
        """Check if a filename matches the expected screenshot naming convention.

        Args:
            filename: The filename to check.

        Returns:
            True if filename matches YYYYMMDD_HHMMSS.png pattern.
        """
        return self.SCREENSHOT_PATTERN.match(filename) is not None

    def validate_screenshot_filename(self, filename: str, date: datetime) -> bool:
        """Validate that a screenshot filename is properly formatted for the given date.

        Args:
            filename: The filename to validate.
            date: The expected date.

        Returns:
            True if filename is valid and matches the date.
        """
        if not self._is_valid_screenshot_name(filename):
            return False

        # Extract date from filename (YYYYMMDD part)
        date_str = filename[:8]
        expected_date_str = date.strftime("%Y%m%d")

        return date_str == expected_date_str

    def get_date_directory_path(self, date: datetime) -> Path:
        """Get the directory path for a specific date.

        Args:
            date: The date for which to get the directory path.

        Returns:
            Path object representing the date-based directory.
        """
        year = date.strftime("%Y")
        month = date.strftime("%m")
        day = date.strftime("%d")
        return self._base_path / year / month / day
