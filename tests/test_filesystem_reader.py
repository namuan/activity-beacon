from datetime import datetime
from pathlib import Path

import pytest

from activity_beacon.file_storage.filesystem_reader import (
    FileSystemReader,
    ValidationReport,
)


class TestFileSystemReader:
    """Test suite for FileSystemReader."""

    def test_init_with_path_object(self, tmp_path: Path) -> None:
        reader = FileSystemReader(tmp_path)
        assert reader._base_path == tmp_path

    def test_init_with_string_path(self, tmp_path: Path) -> None:
        reader = FileSystemReader(str(tmp_path))
        assert reader._base_path == tmp_path

    def test_init_with_tilde_expansion(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HOME", str(tmp_path))
        reader = FileSystemReader("~/test_dir")
        assert reader._base_path == tmp_path / "test_dir"

    def test_validate_date_directory_not_exists(self, tmp_path: Path) -> None:
        reader = FileSystemReader(tmp_path)
        date = datetime(2024, 3, 15, 10, 30, 0)

        report = reader.validate_date_directory(date)

        assert report.is_valid is False
        assert len(report.errors) == 1
        assert "does not exist" in report.errors[0]
        assert len(report.warnings) == 0
        assert len(report.found_screenshots) == 0
        assert len(report.found_data_files) == 0

    def test_validate_date_directory_is_file(self, tmp_path: Path) -> None:
        reader = FileSystemReader(tmp_path)
        date = datetime(2024, 3, 15, 10, 30, 0)

        # Create a file instead of directory
        date_path = tmp_path / "2024" / "03" / "15"
        date_path.parent.mkdir(parents=True)
        date_path.touch()

        report = reader.validate_date_directory(date)

        assert report.is_valid is False
        assert len(report.errors) == 1
        assert "not a directory" in report.errors[0]

    def test_validate_date_directory_empty(self, tmp_path: Path) -> None:
        reader = FileSystemReader(tmp_path)
        date = datetime(2024, 3, 15, 10, 30, 0)

        # Create empty directory
        date_dir = tmp_path / "2024" / "03" / "15"
        date_dir.mkdir(parents=True)

        report = reader.validate_date_directory(date)

        assert report.is_valid is True
        assert len(report.errors) == 0
        assert len(report.warnings) == 2  # No window data, no screenshots
        assert "No window data file found" in report.warnings[0]
        assert "No valid screenshot files found" in report.warnings[1]

    def test_validate_date_directory_with_valid_screenshots(
        self, tmp_path: Path
    ) -> None:
        reader = FileSystemReader(tmp_path)
        date = datetime(2024, 3, 15, 10, 30, 0)

        # Create directory with valid screenshots
        date_dir = tmp_path / "2024" / "03" / "15"
        date_dir.mkdir(parents=True)
        (date_dir / "20240315_103000.png").touch()
        (date_dir / "20240315_103030.png").touch()
        (date_dir / "20240315_104000.png").touch()

        report = reader.validate_date_directory(date)

        assert report.is_valid is True
        assert len(report.errors) == 0
        assert len(report.found_screenshots) == 3
        assert "20240315_103000.png" in report.found_screenshots
        assert "20240315_103030.png" in report.found_screenshots
        assert "20240315_104000.png" in report.found_screenshots

    def test_validate_date_directory_with_window_data(self, tmp_path: Path) -> None:
        reader = FileSystemReader(tmp_path)
        date = datetime(2024, 3, 15, 10, 30, 0)

        # Create directory with window data file
        date_dir = tmp_path / "2024" / "03" / "15"
        date_dir.mkdir(parents=True)
        (date_dir / "window_data.jsonl").touch()

        report = reader.validate_date_directory(date)

        assert report.is_valid is True
        assert len(report.errors) == 0
        assert len(report.found_data_files) == 1
        assert "window_data.jsonl" in report.found_data_files

    def test_validate_date_directory_complete(self, tmp_path: Path) -> None:
        reader = FileSystemReader(tmp_path)
        date = datetime(2024, 3, 15, 10, 30, 0)

        # Create complete directory structure
        date_dir = tmp_path / "2024" / "03" / "15"
        date_dir.mkdir(parents=True)
        (date_dir / "20240315_103000.png").touch()
        (date_dir / "20240315_104000.png").touch()
        (date_dir / "window_data.jsonl").touch()

        report = reader.validate_date_directory(date)

        assert report.is_valid is True
        assert len(report.errors) == 0
        assert len(report.warnings) == 0
        assert len(report.found_screenshots) == 2
        assert len(report.found_data_files) == 1

    def test_validate_date_directory_invalid_screenshot_names(
        self, tmp_path: Path
    ) -> None:
        reader = FileSystemReader(tmp_path)
        date = datetime(2024, 3, 15, 10, 30, 0)

        # Create directory with invalid screenshot names
        date_dir = tmp_path / "2024" / "03" / "15"
        date_dir.mkdir(parents=True)
        (date_dir / "invalid_name.png").touch()
        (date_dir / "20240315.png").touch()
        (date_dir / "screenshot.png").touch()

        report = reader.validate_date_directory(date)

        assert report.is_valid is True
        assert len(report.errors) == 0
        assert len(report.warnings) >= 3  # One for each invalid PNG
        assert len(report.found_screenshots) == 0

    def test_validate_date_directory_permission_error(self, tmp_path: Path) -> None:
        reader = FileSystemReader(tmp_path)
        date = datetime(2024, 3, 15, 10, 30, 0)

        # Create directory and make it unreadable
        date_dir = tmp_path / "2024" / "03" / "15"
        date_dir.mkdir(parents=True)
        date_dir.chmod(0o000)

        try:
            report = reader.validate_date_directory(date)

            assert report.is_valid is False
            assert len(report.errors) >= 1
            assert "Permission denied" in report.errors[0]
            assert reader.last_error_msg is not None
        finally:
            # Cleanup: restore permissions
            date_dir.chmod(0o755)

    def test_validate_date_directory_window_data_is_directory(
        self, tmp_path: Path
    ) -> None:
        reader = FileSystemReader(tmp_path)
        date = datetime(2024, 3, 15, 10, 30, 0)

        # Create window_data.jsonl as directory instead of file
        date_dir = tmp_path / "2024" / "03" / "15"
        date_dir.mkdir(parents=True)
        (date_dir / "window_data.jsonl").mkdir()

        report = reader.validate_date_directory(date)

        assert report.is_valid is False
        assert len(report.errors) == 1
        assert "not a file" in report.errors[0]

    def test_is_valid_screenshot_name_valid_cases(self, tmp_path: Path) -> None:
        reader = FileSystemReader(tmp_path)

        assert reader._is_valid_screenshot_name("20240315_103000.png") is True
        assert reader._is_valid_screenshot_name("20241231_235959.png") is True
        assert reader._is_valid_screenshot_name("20240101_000000.png") is True

    def test_is_valid_screenshot_name_invalid_cases(self, tmp_path: Path) -> None:
        reader = FileSystemReader(tmp_path)

        assert reader._is_valid_screenshot_name("invalid.png") is False
        assert reader._is_valid_screenshot_name("20240315.png") is False
        assert reader._is_valid_screenshot_name("2024-03-15_103000.png") is False
        assert reader._is_valid_screenshot_name("20240315_10300.png") is False
        assert reader._is_valid_screenshot_name("20240315_103000.jpg") is False
        assert reader._is_valid_screenshot_name("screenshot.png") is False

    def test_validate_screenshot_filename_valid(self, tmp_path: Path) -> None:
        reader = FileSystemReader(tmp_path)
        date = datetime(2024, 3, 15, 10, 30, 0)

        assert reader.validate_screenshot_filename("20240315_103000.png", date) is True
        assert reader.validate_screenshot_filename("20240315_235959.png", date) is True

    def test_validate_screenshot_filename_wrong_date(self, tmp_path: Path) -> None:
        reader = FileSystemReader(tmp_path)
        date = datetime(2024, 3, 15, 10, 30, 0)

        assert reader.validate_screenshot_filename("20240316_103000.png", date) is False
        assert reader.validate_screenshot_filename("20240314_103000.png", date) is False

    def test_validate_screenshot_filename_invalid_format(self, tmp_path: Path) -> None:
        reader = FileSystemReader(tmp_path)
        date = datetime(2024, 3, 15, 10, 30, 0)

        assert reader.validate_screenshot_filename("invalid.png", date) is False
        assert reader.validate_screenshot_filename("20240315.png", date) is False

    def test_get_date_directory_path(self, tmp_path: Path) -> None:
        reader = FileSystemReader(tmp_path)
        date = datetime(2024, 3, 15, 10, 30, 0)

        path = reader.get_date_directory_path(date)

        assert path == tmp_path / "2024" / "03" / "15"

    def test_get_date_directory_path_padding(self, tmp_path: Path) -> None:
        reader = FileSystemReader(tmp_path)
        date = datetime(2024, 1, 5, 10, 30, 0)

        path = reader.get_date_directory_path(date)

        assert path == tmp_path / "2024" / "01" / "05"

    def test_validation_report_immutability(self) -> None:
        report = ValidationReport(
            is_valid=True,
            errors=("error1", "error2"),
            warnings=("warning1",),
            found_screenshots=("screenshot1.png",),
            found_data_files=("window_data.jsonl",),
        )

        # Verify it's frozen (dataclass with frozen=True raises FrozenInstanceError on assignment)
        with pytest.raises((AttributeError, Exception)):
            report.is_valid = False  # type: ignore[misc]

    def test_validate_date_directory_mixed_files(self, tmp_path: Path) -> None:
        reader = FileSystemReader(tmp_path)
        date = datetime(2024, 3, 15, 10, 30, 0)

        # Create directory with mix of valid and invalid files
        date_dir = tmp_path / "2024" / "03" / "15"
        date_dir.mkdir(parents=True)
        (date_dir / "20240315_103000.png").touch()  # Valid
        (date_dir / "20240315_104000.png").touch()  # Valid
        (date_dir / "invalid.png").touch()  # Invalid
        (date_dir / "readme.txt").touch()  # Not PNG
        (date_dir / "window_data.jsonl").touch()  # Data file

        report = reader.validate_date_directory(date)

        assert report.is_valid is True
        assert len(report.errors) == 0
        assert len(report.found_screenshots) == 2
        assert len(report.found_data_files) == 1
        # Should have warning about invalid PNG
        assert any("invalid naming convention" in w for w in report.warnings)
