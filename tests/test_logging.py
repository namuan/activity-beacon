import logging
from pathlib import Path
import re
import uuid

import pytest

from activity_beacon.logging import (
    get_default_log_dir,
    get_level_name,
    get_logger,
    setup_logging,
)


class TestGetDefaultLogDir:
    def test_returns_correct_path(self) -> None:
        expected = Path.home() / ".logs" / "activity-beacon"
        assert get_default_log_dir() == expected


class TestGetLevelName:
    def test_debug_level(self) -> None:
        assert get_level_name(logging.DEBUG) == "DEBUG"

    def test_info_level(self) -> None:
        assert get_level_name(logging.INFO) == "INFO"

    def test_warning_level(self) -> None:
        assert get_level_name(logging.WARNING) == "WARNING"

    def test_error_level(self) -> None:
        assert get_level_name(logging.ERROR) == "ERROR"

    def test_critical_level(self) -> None:
        assert get_level_name(logging.CRITICAL) == "CRITICAL"


class TestGetLogger:
    def test_returns_logger_instance(self) -> None:
        logger = get_logger(f"test_{uuid.uuid4().hex[:8]}")
        assert isinstance(logger, logging.Logger)

    def test_returns_same_logger_for_same_name(self) -> None:
        name = f"test_{uuid.uuid4().hex[:8]}"
        logger1 = get_logger(name)
        logger2 = get_logger(name)
        assert logger1 is logger2

    def test_sets_debug_level(self) -> None:
        logger = get_logger(f"test_{uuid.uuid4().hex[:8]}")
        assert logger.level == logging.DEBUG

    def test_console_handler_added(self) -> None:
        logger = get_logger(f"test_{uuid.uuid4().hex[:8]}")
        handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(handlers) == 1

    def test_console_handler_info_level(self) -> None:
        logger = get_logger(f"test_{uuid.uuid4().hex[:8]}")
        stream_handler = next(
            h for h in logger.handlers if isinstance(h, logging.StreamHandler)
        )
        assert stream_handler.level == logging.INFO

    def test_log_format(self, tmp_path: Path) -> None:
        logger = get_logger(f"test_{uuid.uuid4().hex[:8]}", tmp_path)
        logger.info("test message")

        # Flush all handlers to ensure log is written to file
        for handler in logger.handlers:
            handler.flush()

        # Check that file handler is attached
        file_handlers = [
            h for h in logger.handlers if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) == 1
        assert file_handlers[0].formatter is not None
        format_string = file_handlers[0].formatter._fmt
        assert format_string == "%(asctime)s - %(levelname)s - %(message)s"

    def test_log_file_created(self, tmp_path: Path) -> None:
        logger = get_logger(f"test_{uuid.uuid4().hex[:8]}", tmp_path)
        logger.info("test message")

        # Flush all handlers to ensure log is written to file
        for handler in logger.handlers:
            handler.flush()

        log_files = list(tmp_path.glob("*.log"))
        assert len(log_files) == 1
        assert log_files[0].name.startswith("activity-beacon-")

    def test_log_file_content_format(self, tmp_path: Path) -> None:
        logger = get_logger(f"test_{uuid.uuid4().hex[:8]}", tmp_path)
        logger.info("test message")

        # Flush all handlers to ensure log is written to file
        for handler in logger.handlers:
            handler.flush()

        log_file = next(iter(tmp_path.glob("*.log")))
        log_content = log_file.read_text().strip()

        # Format: YYYY-MM-DD HH:MM:SS - LEVEL - message
        pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} - INFO - test message"
        assert re.match(
            pattern, log_content
        ), f"Log line doesn't match pattern: {log_content}"

    def test_log_directory_created_if_not_exists(self, tmp_path: Path) -> None:
        log_dir = tmp_path / "logs"
        assert not log_dir.exists()

        # Create parent directory first
        tmp_path.mkdir(parents=True, exist_ok=True)
        get_logger(f"test_{uuid.uuid4().hex[:8]}", log_dir)

        # Directory should be created by mkdir(parents=True, exist_ok=True)
        assert log_dir.exists()

    def test_unicode_messages(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        logger = get_logger(f"test_{uuid.uuid4().hex[:8]}", tmp_path)
        logger.info("Test unicode: 中文 日本语 العربية")

        assert len(caplog.records) == 1
        assert "中文" in caplog.text
        assert "日本语" in caplog.text
        assert "العربية" in caplog.text

    def test_multiple_log_levels(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        logger = get_logger(f"test_{uuid.uuid4().hex[:8]}", tmp_path)

        logger.debug("debug message")
        logger.info("info message")
        logger.warning("warning message")
        logger.error("error message")
        logger.critical("critical message")

        assert len(caplog.records) == 5
        assert caplog.records[0].levelname == "DEBUG"
        assert caplog.records[1].levelname == "INFO"
        assert caplog.records[2].levelname == "WARNING"
        assert caplog.records[3].levelname == "ERROR"
        assert caplog.records[4].levelname == "CRITICAL"

    def test_different_loggers_use_different_files(self, tmp_path: Path) -> None:
        logger1 = get_logger(f"test1_{uuid.uuid4().hex[:8]}", tmp_path)
        logger2 = get_logger(f"test2_{uuid.uuid4().hex[:8]}", tmp_path)

        logger1.info("message from component1")
        logger2.info("message from component2")

        # Flush all handlers
        for logger in [logger1, logger2]:
            for handler in logger.handlers:
                handler.flush()

        log_files = list(tmp_path.glob("*.log"))
        assert len(log_files) == 1  # Both loggers write to same date-based file


class TestSetupLogging:
    def test_creates_multiple_loggers(self, tmp_path: Path) -> None:
        loggers = setup_logging(tmp_path)

        assert len(loggers) == 4
        assert "activity_beacon" in loggers
        assert "activity_beacon.screenshot" in loggers
        assert "activity_beacon.window_tracking" in loggers
        assert "activity_beacon.file_storage" in loggers

    def test_returns_dict_of_loggers(self, tmp_path: Path) -> None:
        loggers = setup_logging(tmp_path)

        for logger in loggers.values():
            assert isinstance(logger, logging.Logger)

    def test_loggers_use_same_log_directory(self, tmp_path: Path) -> None:
        loggers = setup_logging(tmp_path)

        # Write a log message from each logger to ensure file is created
        for logger_name, logger in loggers.items():
            logger.info(f"Test message from {logger_name}")

        # Flush all handlers to ensure logs are written to file
        for logger in loggers.values():
            for handler in logger.handlers:
                handler.flush()

        log_files = list(tmp_path.glob("*.log"))
        assert len(log_files) == 1  # All loggers share the same date-based file

    def test_loggers_created_with_debug_level(self, tmp_path: Path) -> None:
        loggers = setup_logging(tmp_path)

        for logger in loggers.values():
            assert logger.level == logging.DEBUG
