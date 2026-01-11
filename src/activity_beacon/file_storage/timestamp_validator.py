from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class TimestampValidationResult:
    is_valid: bool
    error_message: str | None = None
    parsed_datetime: datetime | None = None


class TimestampValidator:
    """Validates ISO 8601 timestamps for window data."""

    def __init__(  # type: ignore[reportMissingSuperCall]
        self,
        *,
        allow_naive: bool = False,
        require_tz: bool = False,
        allow_microseconds: bool = True,
    ) -> None:
        """Initialize the timestamp validator.

        Args:
            allow_naive: Allow naive timestamps (no timezone). Defaults to False.
            require_tz: Require timezone info. Defaults to False.
            allow_microseconds: Allow microseconds in timestamps. Defaults to True.
        """
        self._allow_naive = allow_naive
        self._require_tz = require_tz
        self._allow_microseconds = allow_microseconds

    def validate(self, timestamp_str: str) -> TimestampValidationResult:
        """Validate an ISO 8601 timestamp string.

        Args:
            timestamp_str: The timestamp string to validate.

        Returns:
            TimestampValidationResult with validation status and details.
        """
        if type(timestamp_str) is not str:
            return TimestampValidationResult(
                is_valid=False,
                error_message="Timestamp must be a string",
                parsed_datetime=None,
            )

        if not timestamp_str.strip():
            return TimestampValidationResult(
                is_valid=False,
                error_message="Timestamp string cannot be empty",
                parsed_datetime=None,
            )

        try:
            parsed = datetime.fromisoformat(timestamp_str)
        except ValueError:
            return TimestampValidationResult(
                is_valid=False,
                error_message="Invalid ISO 8601 format",
                parsed_datetime=None,
            )

        error_message: str | None = None
        if self._require_tz and parsed.tzinfo is None:
            error_message = "Timestamp must include timezone information"
        elif not self._allow_naive and parsed.tzinfo is None:
            error_message = "Naive timestamps are not allowed"
        elif not self._allow_microseconds and parsed.microsecond != 0:
            error_message = "Microseconds are not allowed"

        if error_message is not None:
            return TimestampValidationResult(
                is_valid=False,
                error_message=error_message,
                parsed_datetime=None,
            )

        return TimestampValidationResult(
            is_valid=True,
            error_message=None,
            parsed_datetime=parsed,
        )

    def validate_with_tz(self, timestamp_str: str) -> TimestampValidationResult:
        """Validate a timestamp and ensure it has timezone info.

        Returns a timestamp converted to UTC if it was naive.

        Args:
            timestamp_str: The timestamp string to validate.

        Returns:
            TimestampValidationResult with UTC datetime if valid.
        """
        result = self.validate(timestamp_str)

        if not result.is_valid or result.parsed_datetime is None:
            return result

        if result.parsed_datetime.tzinfo is None:
            aware_dt = result.parsed_datetime.replace(tzinfo=UTC)
            return TimestampValidationResult(
                is_valid=True,
                error_message=None,
                parsed_datetime=aware_dt,
            )

        utc_dt = result.parsed_datetime.astimezone(UTC)
        return TimestampValidationResult(
            is_valid=True,
            error_message=None,
            parsed_datetime=utc_dt,
        )

    def convert_to_utc(self, timestamp_str: str) -> str | None:
        """Convert a valid timestamp string to UTC ISO 8601 format.

        Args:
            timestamp_str: The timestamp string to convert.

        Returns:
            UTC ISO 8601 formatted string, or None if invalid.
        """
        result = self.validate_with_tz(timestamp_str)

        if result.is_valid and result.parsed_datetime is not None:
            return result.parsed_datetime.isoformat()

        return None


def convert_to_utc(timestamp_str: str) -> str | None:
    """Convert a valid timestamp string to UTC ISO 8601 format.

    Args:
        timestamp_str: The timestamp string to convert.

    Returns:
        UTC ISO 8601 formatted string, or None if invalid.
    """
    validator = TimestampValidator()
    return validator.convert_to_utc(timestamp_str)


def parse_timestamp(timestamp_str: str) -> datetime | None:
    """Parse an ISO 8601 timestamp string to a datetime object.

    Args:
        timestamp_str: The timestamp string to parse.

    Returns:
        datetime object if valid, None otherwise.
    """
    try:
        return datetime.fromisoformat(timestamp_str)
    except (ValueError, TypeError):
        return None


def format_timestamp(
    dt: datetime,
    *,
    include_tz: bool = True,
) -> str:
    """Format a datetime object as an ISO 8601 string.

    Args:
        dt: The datetime to format.
        include_tz: Include timezone info. Defaults to True.

    Returns:
        ISO 8601 formatted string.
    """
    if dt.tzinfo is None and include_tz:
        dt = dt.replace(tzinfo=UTC)

    return dt.isoformat()


def ensure_tz_aware(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware.

    Args:
        dt: The datetime to process.

    Returns:
        Timezone-aware datetime (UTC if was naive).
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt
