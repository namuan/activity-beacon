from datetime import date
import logging
from pathlib import Path

YEAR_DIGITS = 4
MONTH_DIGITS = 2
DAY_DIGITS = 2


class FileSystemReader:
    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path
        self.last_error_msg: str | None = None

    def get_available_dates(self) -> list[date]:
        results: list[date] = []
        self.last_error_msg = None
        if not self.validate_base_directory():
            return results
        try:
            for year_dir in sorted(self.base_path.iterdir()):
                results.extend(self._process_year_dir(year_dir))
        except PermissionError as e:
            self.last_error_msg = f"Permission denied: {self.base_path}"
            logging.error("Permission error scanning base directory: %s", e)
        except OSError as e:
            self.last_error_msg = str(e)
            logging.error("OS error scanning base directory: %s", e)
        return sorted(results)

    def _process_year_dir(self, year_dir: Path) -> list[date]:
        """Process a year directory and return all available dates."""
        results: list[date] = []
        if not year_dir.is_dir():
            return results
        if not year_dir.name.isdigit() or len(year_dir.name) != YEAR_DIGITS:
            return results
        for month_dir in sorted(year_dir.iterdir()):
            results.extend(self._process_month_dir(month_dir, year_dir))
        return results

    @staticmethod
    def _process_month_dir(month_dir: Path, year_dir: Path) -> list[date]:
        """Process a month directory and return all available dates."""
        results: list[date] = []
        if not month_dir.is_dir():
            return results
        if not month_dir.name.isdigit() or len(month_dir.name) != MONTH_DIGITS:
            return results
        for day_dir in sorted(month_dir.iterdir()):
            results.extend(
                FileSystemReader._process_day_dir(day_dir, year_dir, month_dir)
            )
        return results

    @staticmethod
    def _process_day_dir(day_dir: Path, year_dir: Path, month_dir: Path) -> list[date]:
        """Process a day directory and return available date if valid."""
        if not day_dir.is_dir():
            return []
        if not day_dir.name.isdigit() or len(day_dir.name) != DAY_DIGITS:
            return []
        try:
            y = int(year_dir.name)
            m = int(month_dir.name)
            d = int(day_dir.name)
            return [date(y, m, d)]
        except ValueError:
            return []

    def get_video_path(self, d: date) -> Path | None:
        try:
            date_dir = (
                self.base_path / f"{d.year:04d}" / f"{d.month:02d}" / f"{d.day:02d}"
            )
            video_name = f"timelapse-{d.strftime("%Y%m%d")}.mp4"
            p = date_dir / video_name
            return p if p.exists() and p.is_file() else None
        except PermissionError as e:
            self.last_error_msg = f"Permission denied: {date_dir}"
            logging.error("Permission error accessing video path: %s", e)
            return None

    def video_exists(self, d: date) -> bool:
        return self.get_video_path(d) is not None

    def get_window_data_path(self, d: date) -> Path | None:
        try:
            date_dir = (
                self.base_path / f"{d.year:04d}" / f"{d.month:02d}" / f"{d.day:02d}"
            )
            p = date_dir / "window_data.jsonl"
            return p if p.exists() and p.is_file() else None
        except PermissionError as e:
            self.last_error_msg = f"Permission denied: {date_dir}"
            logging.error("Permission error accessing window data path: %s", e)
            return None

    def validate_base_directory(self) -> bool:
        return self.base_path.exists() and self.base_path.is_dir()
