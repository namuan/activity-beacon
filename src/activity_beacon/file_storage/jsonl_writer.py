from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
import json
from pathlib import Path

from activity_beacon.logging import get_logger

logger = get_logger("activity_beacon.file_storage")


def _format_timestamp(timestamp: datetime) -> str:
    """Format a datetime object as ISO 8601 string.

    Args:
        timestamp: The datetime to format.

    Returns:
        ISO 8601 formatted string with timezone info.
    """
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return timestamp.isoformat()


class JSONLWriter:
    """Writes window data entries to newline-delimited JSON files."""

    def __init__(self, file_path: Path | str) -> None:  # type: ignore[reportMissingSuperCall]
        """Initialize the JSONL writer with a file path.

        Args:
            file_path: Path to the JSONL file to write to.
        """
        self._file_path = Path(file_path)
        self._last_error_msg: str | None = None
        logger.debug(f"Initialized JSONLWriter with file path: {self._file_path}")

    @property
    def last_error_msg(self) -> str | None:
        """Return the last error message, if any."""
        return self._last_error_msg

    def _serialize_entry(self, entry: Mapping[str, object]) -> str:  # noqa: PLR6301
        """Serialize a dictionary entry to a JSON line.

        Handles datetime serialization and converts to JSON string.

        Args:
            entry: The dictionary to serialize.

        Returns:
            A JSON string (single line).
        """
        serialized: dict[str, object] = {}
        for key, value in entry.items():
            if isinstance(value, datetime):
                serialized[key] = _format_timestamp(value)
            else:
                serialized[key] = value
        return json.dumps(serialized, ensure_ascii=False)

    def write(self, entry: Mapping[str, object]) -> None:
        """Write a single entry to the JSONL file.

        Appends the entry as a new line. Creates the file if it doesn't exist.

        Args:
            entry: The dictionary entry to write.

        Raises:
            OSError: If file write fails due to permissions or other I/O issues.
        """
        try:
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            json_line = self._serialize_entry(entry)
            with self._file_path.open("a", encoding="utf-8") as f:
                f.write(json_line + "\n")
            logger.debug(f"Wrote entry to {self._file_path}")
        except PermissionError as e:
            error_msg = f"Permission denied writing to {self._file_path}: {e}"
            logger.error(error_msg)
            self._last_error_msg = error_msg
            raise OSError(error_msg) from e
        except OSError as e:
            error_msg = f"Failed to write to {self._file_path}: {e}"
            logger.error(error_msg)
            self._last_error_msg = error_msg
            raise OSError(error_msg) from e

    def write_batch(self, entries: Sequence[Mapping[str, object]]) -> None:
        """Write multiple entries to the JSONL file.

        Args:
            entries: List of dictionary entries to write.
        """
        for entry in entries:
            self.write(entry)

    def get_file_path(self) -> Path:
        """Return the file path being written to.

        Returns:
            The Path object for the output file.
        """
        return self._file_path

    def file_exists(self) -> bool:
        """Check if the output file exists.

        Returns:
            True if the file exists, False otherwise.
        """
        return self._file_path.exists()
