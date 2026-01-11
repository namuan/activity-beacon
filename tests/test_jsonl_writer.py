from datetime import UTC, datetime
import json
from pathlib import Path

import pytest

from activity_beacon.file_storage.jsonl_writer import JSONLWriter


class TestJSONLWriter:
    def test_init_with_path_object(self, tmp_path: Path) -> None:
        writer = JSONLWriter(tmp_path / "data.jsonl")
        assert writer.get_file_path() == tmp_path / "data.jsonl"

    def test_init_with_string_path(self, tmp_path: Path) -> None:
        writer = JSONLWriter(str(tmp_path / "data.jsonl"))
        assert writer.get_file_path() == tmp_path / "data.jsonl"

    def test_write_creates_file(self, tmp_path: Path) -> None:
        writer = JSONLWriter(tmp_path / "data.jsonl")
        entry = {"key": "value"}
        writer.write(entry)
        assert (tmp_path / "data.jsonl").exists()

    def test_write_single_entry(self, tmp_path: Path) -> None:
        writer = JSONLWriter(tmp_path / "data.jsonl")
        entry = {"name": "test", "value": 42}
        writer.write(entry)
        lines = (tmp_path / "data.jsonl").read_text().strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["name"] == "test"
        assert parsed["value"] == 42

    def test_write_multiple_entries(self, tmp_path: Path) -> None:
        writer = JSONLWriter(tmp_path / "data.jsonl")
        entries = [
            {"id": 1, "name": "first"},
            {"id": 2, "name": "second"},
            {"id": 3, "name": "third"},
        ]
        writer.write_batch(entries)
        lines = (tmp_path / "data.jsonl").read_text().strip().split("\n")
        assert len(lines) == 3
        for i, line in enumerate(lines):
            parsed = json.loads(line)
            assert parsed["id"] == i + 1
            assert parsed["name"] == ["first", "second", "third"][i]

    def test_write_append_mode(self, tmp_path: Path) -> None:
        writer = JSONLWriter(tmp_path / "data.jsonl")
        writer.write({"id": 1})
        writer.write({"id": 2})
        lines = (tmp_path / "data.jsonl").read_text().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["id"] == 1
        assert json.loads(lines[1])["id"] == 2

    def test_write_datetime_iso_format(self, tmp_path: Path) -> None:
        writer = JSONLWriter(tmp_path / "data.jsonl")
        timestamp = datetime(2024, 3, 15, 14, 30, 45, tzinfo=UTC)
        entry = {"timestamp": timestamp}
        writer.write(entry)
        line = (tmp_path / "data.jsonl").read_text().strip()
        parsed = json.loads(line)
        assert parsed["timestamp"] == "2024-03-15T14:30:45+00:00"

    def test_write_datetime_naive_converted_to_utc(self, tmp_path: Path) -> None:
        writer = JSONLWriter(tmp_path / "data.jsonl")
        timestamp = datetime(2024, 3, 15, 14, 30, 45)
        entry = {"timestamp": timestamp}
        writer.write(entry)
        line = (tmp_path / "data.jsonl").read_text().strip()
        parsed = json.loads(line)
        assert "+00:00" in parsed["timestamp"]
        assert "2024-03-15T14:30:45" in parsed["timestamp"]

    def test_write_tuple_converted_to_list(self, tmp_path: Path) -> None:
        writer = JSONLWriter(tmp_path / "data.jsonl")
        entry = {"coords": (1, 2, 3, 4)}
        writer.write(entry)
        line = (tmp_path / "data.jsonl").read_text().strip()
        parsed = json.loads(line)
        assert parsed["coords"] == [1, 2, 3, 4]

    def test_write_creates_parent_directories(self, tmp_path: Path) -> None:
        writer = JSONLWriter(tmp_path / "nested" / "path" / "data.jsonl")
        entry = {"key": "value"}
        writer.write(entry)
        assert (tmp_path / "nested" / "path" / "data.jsonl").exists()

    def test_write_permission_error(self, tmp_path: Path) -> None:
        writer = JSONLWriter(tmp_path / "readonly" / "data.jsonl")
        (tmp_path / "readonly").mkdir()
        (tmp_path / "readonly").chmod(0o444)
        entry = {"key": "value"}
        try:
            with pytest.raises(OSError, match="Permission denied"):
                writer.write(entry)
        finally:
            (tmp_path / "readonly").chmod(0o755)

    def test_file_exists_returns_true_when_file_exists(self, tmp_path: Path) -> None:
        writer = JSONLWriter(tmp_path / "data.jsonl")
        writer.write({"key": "value"})
        assert writer.file_exists() is True

    def test_file_exists_returns_false_when_file_missing(self, tmp_path: Path) -> None:
        writer = JSONLWriter(tmp_path / "data.jsonl")
        assert writer.file_exists() is False

    def test_last_error_msg_initially_none(self, tmp_path: Path) -> None:
        writer = JSONLWriter(tmp_path / "data.jsonl")
        assert writer.last_error_msg is None

    def test_last_error_msg_set_on_error(self, tmp_path: Path) -> None:
        writer = JSONLWriter(tmp_path / "readonly" / "data.jsonl")
        (tmp_path / "readonly").mkdir()
        (tmp_path / "readonly").chmod(0o444)
        with pytest.raises(OSError):
            writer.write({"key": "value"})
        assert writer.last_error_msg is not None
        assert "Permission denied" in writer.last_error_msg

    def test_write_special_characters(self, tmp_path: Path) -> None:
        writer = JSONLWriter(tmp_path / "data.jsonl")
        entry = {"text": 'Hello\nWorld\t"Quotes"', "emoji": "🎉"}
        writer.write(entry)
        line = (tmp_path / "data.jsonl").read_text().strip()
        parsed = json.loads(line)
        assert parsed["text"] == 'Hello\nWorld\t"Quotes"'
        assert parsed["emoji"] == "🎉"

    def test_write_empty_object(self, tmp_path: Path) -> None:
        writer = JSONLWriter(tmp_path / "data.jsonl")
        writer.write({})
        line = (tmp_path / "data.jsonl").read_text().strip()
        assert line == "{}"

    def test_write_nested_object(self, tmp_path: Path) -> None:
        writer = JSONLWriter(tmp_path / "data.jsonl")
        entry = {
            "level1": {
                "level2": {
                    "level3": "deep value",
                }
            }
        }
        writer.write(entry)
        line = (tmp_path / "data.jsonl").read_text().strip()
        parsed = json.loads(line)
        assert parsed["level1"]["level2"]["level3"] == "deep value"

    def test_write_unicode_characters(self, tmp_path: Path) -> None:
        writer = JSONLWriter(tmp_path / "data.jsonl")
        entry = {"chinese": "中文", "japanese": "にほんご", "arabic": "العربية"}
        writer.write(entry)
        line = (tmp_path / "data.jsonl").read_text().strip()
        parsed = json.loads(line)
        assert parsed["chinese"] == "中文"
        assert parsed["japanese"] == "にほんご"
        assert parsed["arabic"] == "العربية"
