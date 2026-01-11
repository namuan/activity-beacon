from datetime import UTC, datetime, timedelta, timezone

from activity_beacon.file_storage.timestamp_validator import (
    TimestampValidator,
    ensure_tz_aware,
    format_timestamp,
    parse_timestamp,
)


class TestTimestampValidator:
    def test_valid_timestamp_with_timezone(self) -> None:
        validator = TimestampValidator()
        result = validator.validate("2024-03-15T14:30:45+00:00")
        assert result.is_valid is True
        assert result.error_message is None
        assert result.parsed_datetime is not None

    def test_valid_timestamp_with_z(self) -> None:
        validator = TimestampValidator()
        result = validator.validate("2024-03-15T14:30:45Z")
        assert result.is_valid is True
        assert result.parsed_datetime is not None

    def test_valid_timestamp_with_microseconds(self) -> None:
        validator = TimestampValidator()
        result = validator.validate("2024-03-15T14:30:45.123456+00:00")
        assert result.is_valid is True
        assert result.parsed_datetime is not None
        assert result.parsed_datetime.microsecond == 123456

    def test_valid_naive_timestamp_when_allowed(self) -> None:
        validator = TimestampValidator(allow_naive=True)
        result = validator.validate("2024-03-15T14:30:45")
        assert result.is_valid is True
        assert result.parsed_datetime is not None
        assert result.parsed_datetime.tzinfo is None

    def test_invalid_naive_timestamp_when_not_allowed(self) -> None:
        validator = TimestampValidator(allow_naive=False)
        result = validator.validate("2024-03-15T14:30:45")
        assert result.is_valid is False
        assert "Naive timestamps are not allowed" in result.error_message

    def test_invalid_empty_string(self) -> None:
        validator = TimestampValidator()
        result = validator.validate("")
        assert result.is_valid is False
        assert "cannot be empty" in result.error_message

    def test_invalid_whitespace_only(self) -> None:
        validator = TimestampValidator()
        result = validator.validate("   ")
        assert result.is_valid is False
        assert "cannot be empty" in result.error_message

    def test_invalid_non_string(self) -> None:
        validator = TimestampValidator()
        result = validator.validate(12345)  # type: ignore[arg-type]
        assert result.is_valid is False
        assert "must be a string" in result.error_message

    def test_invalid_format(self) -> None:
        validator = TimestampValidator()
        result = validator.validate("not-a-timestamp")
        assert result.is_valid is False
        assert "Invalid" in result.error_message

    def test_invalid_date_format(self) -> None:
        validator = TimestampValidator()
        result = validator.validate("15-03-2024T14:30:45")
        assert result.is_valid is False

    def test_require_timezone(self) -> None:
        validator = TimestampValidator(require_tz=True)
        result = validator.validate("2024-03-15T14:30:45")
        assert result.is_valid is False
        assert "timezone" in result.error_message.lower()

    def test_disallow_microseconds(self) -> None:
        validator = TimestampValidator(allow_microseconds=False)
        result = validator.validate("2024-03-15T14:30:45.123456+00:00")
        assert result.is_valid is False
        assert "Microseconds" in result.error_message

    def test_allow_microseconds_by_default(self) -> None:
        validator = TimestampValidator()
        result = validator.validate("2024-03-15T14:30:45.123456+00:00")
        assert result.is_valid is True

    def test_different_timezone_offset(self) -> None:
        validator = TimestampValidator()
        result = validator.validate("2024-03-15T14:30:45+05:30")
        assert result.is_valid is True
        assert result.parsed_datetime is not None

    def test_negative_timezone_offset(self) -> None:
        validator = TimestampValidator()
        result = validator.validate("2024-03-15T14:30:45-08:00")
        assert result.is_valid is True
        assert result.parsed_datetime is not None

    def test_validate_with_tz_returns_utc(self) -> None:
        validator = TimestampValidator()
        result = validator.validate_with_tz("2024-03-15T14:30:45+05:30")
        assert result.is_valid is True
        assert result.parsed_datetime is not None
        assert result.parsed_datetime.tzinfo == UTC

    def test_validate_with_tz_naive_converted(self) -> None:
        validator = TimestampValidator(allow_naive=True)
        result = validator.validate_with_tz("2024-03-15T14:30:45")
        assert result.is_valid is True
        assert result.parsed_datetime is not None
        assert result.parsed_datetime.tzinfo == UTC

    def test_convert_to_utc_valid(self) -> None:
        validator = TimestampValidator()
        result = validator.convert_to_utc("2024-03-15T14:30:45+05:30")
        assert result is not None
        assert "+00:00" in result

    def test_convert_to_utc_invalid(self) -> None:
        validator = TimestampValidator()
        result = validator.convert_to_utc("invalid")
        assert result is None


class TestParseTimestamp:
    def test_parse_valid_timestamp(self) -> None:
        result = parse_timestamp("2024-03-15T14:30:45+00:00")
        assert result is not None
        assert isinstance(result, datetime)

    def test_parse_naive_timestamp(self) -> None:
        result = parse_timestamp("2024-03-15T14:30:45")
        assert result is not None
        assert result.tzinfo is None

    def test_parse_invalid_timestamp(self) -> None:
        result = parse_timestamp("not-a-timestamp")
        assert result is None

    def test_parse_none(self) -> None:
        result = parse_timestamp(None)  # type: ignore[arg-type]
        assert result is None


class TestFormatTimestamp:
    def test_format_with_timezone(self) -> None:
        dt = datetime(2024, 3, 15, 14, 30, 45, tzinfo=UTC)
        result = format_timestamp(dt)
        assert "2024-03-15T14:30:45" in result
        assert "+00:00" in result

    def test_format_naive_adds_utc(self) -> None:
        dt = datetime(2024, 3, 15, 14, 30, 45)
        result = format_timestamp(dt, include_tz=True)
        assert "2024-03-15T14:30:45" in result
        assert "+00:00" in result

    def test_format_without_timezone(self) -> None:
        dt = datetime(2024, 3, 15, 14, 30, 45)
        result = format_timestamp(dt, include_tz=False)
        assert result == "2024-03-15T14:30:45"

    def test_format_preserves_existing_tz(self) -> None:
        tz = timezone(offset=timedelta(hours=5, minutes=30))  # type: ignore[attr-defined,name-defined,unused-ignore]
        dt = datetime(2024, 3, 15, 14, 30, 45, tzinfo=tz)
        result = format_timestamp(dt, include_tz=True)
        assert "+05:30" in result


class TestEnsureTzAware:
    def test_naive_becomes_utc(self) -> None:
        dt = datetime(2024, 3, 15, 14, 30, 45)
        result = ensure_tz_aware(dt)
        assert result.tzinfo == UTC

    def test_already_aware_unchanged(self) -> None:
        dt = datetime(2024, 3, 15, 14, 30, 45, tzinfo=UTC)
        result = ensure_tz_aware(dt)
        assert result == dt
