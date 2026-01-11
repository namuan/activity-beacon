from datetime import datetime
from pathlib import Path

import pytest

from activity_beacon.file_storage.date_directory_manager import DateDirectoryManager


class TestDateDirectoryManager:
    def test_init_with_path_object(self, tmp_path: Path) -> None:
        manager = DateDirectoryManager(tmp_path)
        assert manager._base_path == tmp_path

    def test_init_with_string_path(self, tmp_path: Path) -> None:
        manager = DateDirectoryManager(str(tmp_path))
        assert manager._base_path == tmp_path

    def test_init_with_tilde_expansion(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Mock home directory
        monkeypatch.setenv("HOME", str(tmp_path))
        manager = DateDirectoryManager("~/test_dir")
        assert manager._base_path == tmp_path / "test_dir"

    def test_get_date_directory_structure(self, tmp_path: Path) -> None:
        manager = DateDirectoryManager(tmp_path)
        date = datetime(2024, 3, 15, 10, 30, 0)

        result = manager.get_date_directory(date)

        assert result == tmp_path / "2024" / "03" / "15"

    def test_get_date_directory_padding(self, tmp_path: Path) -> None:
        manager = DateDirectoryManager(tmp_path)
        date = datetime(2024, 1, 5, 10, 30, 0)

        result = manager.get_date_directory(date)

        assert result == tmp_path / "2024" / "01" / "05"

    def test_ensure_date_directory_creates_hierarchy(self, tmp_path: Path) -> None:
        manager = DateDirectoryManager(tmp_path)
        date = datetime(2024, 3, 15, 10, 30, 0)

        result = manager.ensure_date_directory(date)

        assert result.exists()
        assert result.is_dir()
        assert result == tmp_path / "2024" / "03" / "15"

    def test_ensure_date_directory_creates_parents(self, tmp_path: Path) -> None:
        manager = DateDirectoryManager(tmp_path)
        date = datetime(2024, 3, 15, 10, 30, 0)

        manager.ensure_date_directory(date)

        assert (tmp_path / "2024").exists()
        assert (tmp_path / "2024" / "03").exists()
        assert (tmp_path / "2024" / "03" / "15").exists()

    def test_ensure_date_directory_idempotent(self, tmp_path: Path) -> None:
        manager = DateDirectoryManager(tmp_path)
        date = datetime(2024, 3, 15, 10, 30, 0)

        result1 = manager.ensure_date_directory(date)
        result2 = manager.ensure_date_directory(date)

        assert result1 == result2
        assert result1.exists()

    def test_ensure_date_directory_multiple_dates(self, tmp_path: Path) -> None:
        manager = DateDirectoryManager(tmp_path)
        date1 = datetime(2024, 3, 15, 10, 30, 0)
        date2 = datetime(2024, 3, 16, 10, 30, 0)

        dir1 = manager.ensure_date_directory(date1)
        dir2 = manager.ensure_date_directory(date2)

        assert dir1.exists()
        assert dir2.exists()
        assert dir1 != dir2

    def test_ensure_date_directory_permission_error(self, tmp_path: Path) -> None:
        manager = DateDirectoryManager(tmp_path / "readonly")
        # Create parent but make it read-only
        (tmp_path / "readonly").mkdir()
        (tmp_path / "readonly").chmod(0o444)

        date = datetime(2024, 3, 15, 10, 30, 0)

        try:
            with pytest.raises(OSError, match="Failed to create directory"):
                manager.ensure_date_directory(date)
        finally:
            # Cleanup: restore permissions
            (tmp_path / "readonly").chmod(0o755)

    def test_get_screenshot_filename_format(self, tmp_path: Path) -> None:
        manager = DateDirectoryManager(tmp_path)
        timestamp = datetime(2024, 3, 15, 14, 30, 45)

        filename = manager.get_screenshot_filename(timestamp)

        assert filename == "20240315_143045.png"

    def test_get_screenshot_filename_padding(self, tmp_path: Path) -> None:
        manager = DateDirectoryManager(tmp_path)
        timestamp = datetime(2024, 1, 5, 9, 5, 3)

        filename = manager.get_screenshot_filename(timestamp)

        assert filename == "20240105_090503.png"

    def test_get_screenshot_filename_midnight(self, tmp_path: Path) -> None:
        manager = DateDirectoryManager(tmp_path)
        timestamp = datetime(2024, 12, 31, 0, 0, 0)

        filename = manager.get_screenshot_filename(timestamp)

        assert filename == "20241231_000000.png"

    def test_get_screenshot_path_combines_directory_and_filename(
        self, tmp_path: Path
    ) -> None:
        manager = DateDirectoryManager(tmp_path)
        timestamp = datetime(2024, 3, 15, 14, 30, 45)

        path = manager.get_screenshot_path(timestamp)

        expected = tmp_path / "2024" / "03" / "15" / "20240315_143045.png"
        assert path == expected

    def test_get_screenshot_path_different_dates(self, tmp_path: Path) -> None:
        manager = DateDirectoryManager(tmp_path)
        timestamp1 = datetime(2024, 3, 15, 14, 30, 45)
        timestamp2 = datetime(2024, 3, 16, 10, 15, 30)

        path1 = manager.get_screenshot_path(timestamp1)
        path2 = manager.get_screenshot_path(timestamp2)

        assert path1.parent != path2.parent
        assert path1.name == "20240315_143045.png"
        assert path2.name == "20240316_101530.png"

    def test_validate_path_security_valid_path(self, tmp_path: Path) -> None:
        manager = DateDirectoryManager(tmp_path)
        valid_path = tmp_path / "2024" / "03" / "15" / "screenshot.png"

        assert manager.validate_path_security(valid_path) is True

    def test_validate_path_security_base_path(self, tmp_path: Path) -> None:
        manager = DateDirectoryManager(tmp_path)

        assert manager.validate_path_security(tmp_path) is True

    def test_validate_path_security_traversal_attempt(self, tmp_path: Path) -> None:
        manager = DateDirectoryManager(tmp_path / "screenshots")
        # Try to escape to parent directory
        malicious_path = tmp_path / "screenshots" / ".." / "etc" / "passwd"

        assert manager.validate_path_security(malicious_path) is False

    def test_validate_path_security_absolute_outside(self, tmp_path: Path) -> None:
        manager = DateDirectoryManager(tmp_path / "screenshots")
        outside_path = Path("/etc/passwd")

        assert manager.validate_path_security(outside_path) is False

    def test_validate_path_security_symlink_outside(self, tmp_path: Path) -> None:
        manager = DateDirectoryManager(tmp_path / "screenshots")
        (tmp_path / "screenshots").mkdir()
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()

        # Create symlink inside base that points outside
        symlink = tmp_path / "screenshots" / "link"
        symlink.symlink_to(outside_dir)

        # The symlink itself should fail validation when resolved
        assert manager.validate_path_security(symlink) is False
