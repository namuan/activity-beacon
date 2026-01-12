from __future__ import annotations

import argparse
import contextlib
from datetime import datetime
import logging
from pathlib import Path
import sys
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from .calendar_widget import CalendarWidget
from .filesystem_reader import FileSystemReader
from .video_player import VideoPlayerWidget
from .window_data_parser import WindowDataParser
from .window_data_timeline import WindowDataTimeline

if TYPE_CHECKING:
    from datetime import date as date_type

    from PyQt6.QtCore import QDate
    from PyQt6.QtGui import QResizeEvent

    from .window_data_parser import WindowDataEntry


class MainWindow(QMainWindow):
    def __init__(self, base_dir: Path | None = None) -> None:
        super().__init__()
        self._base_dir = base_dir or (Path.home() / "Documents" / "Screenshots")
        self._fs = FileSystemReader(self._base_dir)
        self._parser = WindowDataParser()

        self._calendar: CalendarWidget | None = None
        self._video_player: VideoPlayerWidget | None = None
        self._timeline: WindowDataTimeline | None = None
        self._current_date: QDate | None = None
        self._progress: QProgressBar | None = None

        self.setWindowTitle("Activity Beacon")
        with contextlib.suppress(Exception):
            self.setWindowIcon(
                self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
            )
        self.setMinimumSize(1000, 650)
        self.setup_ui()

    def setup_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        central.setLayout(root)
        self.setCentralWidget(central)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.hide()
        self.statusBar().addPermanentWidget(self._progress)

        self._video_player = VideoPlayerWidget()
        root.addWidget(self._video_player)

        bottom = QWidget()
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(0)
        bottom.setLayout(bottom_layout)
        root.addWidget(bottom)

        self._calendar = CalendarWidget(self._fs)
        bottom_layout.addWidget(self._calendar)

        right = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right.setLayout(right_layout)
        bottom_layout.addWidget(right)

        right_layout.addWidget(self._video_player.get_controls_widget())

        self._timeline = WindowDataTimeline()
        right_layout.addWidget(self._timeline)

        right_layout.setStretch(0, 0)
        right_layout.setStretch(1, 1)

        root.setStretch(0, 8)
        root.setStretch(1, 2)
        bottom_layout.setStretch(0, 3)
        bottom_layout.setStretch(1, 7)

        self._calendar.date_selected.connect(self.on_date_selected)
        self._calendar.error_occurred.connect(self.on_component_error)
        self._video_player.error_occurred.connect(self.on_component_error)
        self._calendar.loading_started.connect(self._progress.show)
        self._calendar.loading_finished.connect(self._progress.hide)
        self._video_player.loading_changed.connect(self._progress.setVisible)

    def on_date_selected(self, date: QDate) -> None:
        self._current_date = date
        py_date = datetime(year=date.year(), month=date.month(), day=date.day()).date()

        self.statusBar().showMessage("Loading video…", 2000)
        video_path = self._fs.get_video_path(py_date)
        if video_path is None:
            self._handle_no_video_available(py_date)
            return

        self._load_video_and_data(video_path, date, py_date)

    def _handle_no_video_available(self, py_date: date_type) -> None:
        """Handle case when no video is available for the selected date."""
        with contextlib.suppress(Exception):
            logging.warning("No timelapse video available for date %s", py_date)
        self.display_error("No timelapse video available for this date")
        if self._video_player:
            self._video_player.pause()
        if self._timeline:
            self._timeline.clear()

    def _load_video_and_data(
        self, video_path: Path, date: QDate, py_date: date_type
    ) -> None:
        """Load video and window data for the selected date."""
        if self._video_player:
            self._video_player.load_video(video_path)
            self._video_player.play()

        entries = self._load_window_data(py_date)
        video_start_dt = MainWindow._get_video_start_datetime(entries, date)

        if self._timeline and self._video_player and video_start_dt:
            self._timeline.bind_to_player(self._video_player, video_start_dt)
            self._setup_duration_changed_handler(video_start_dt)

    def _load_window_data(self, py_date: date_type) -> list[WindowDataEntry]:
        """Load window data for the selected date."""
        entries: list[WindowDataEntry] = []
        wd_path = self._fs.get_window_data_path(py_date)
        if wd_path is not None:
            self.statusBar().showMessage("Loading window data…", 2000)
            if self._progress:
                self._progress.show()
            entries = self._parser.parse_file(wd_path)
            self.update_window_data(entries)
            if self._progress:
                self._progress.hide()
        elif self._timeline:
            self._timeline.clear()
        return entries

    @staticmethod
    def _get_video_start_datetime(
        entries: list[WindowDataEntry], date: QDate
    ) -> datetime | None:
        """Get the video start datetime based on entries or date."""
        if entries:
            return entries[0].timestamp
        return datetime(year=date.year(), month=date.month(), day=date.day())

    def _setup_duration_changed_handler(self, video_start_dt: datetime) -> None:
        """Setup the duration changed signal handler."""
        if self._video_player and hasattr(self._video_player, "_player"):
            self._video_player._player.durationChanged.connect(
                lambda dur: self._timeline
                and self._timeline.set_video_timing(video_start_dt, int(dur))
            )

    def display_video(self, video_path: Path) -> None:
        if self._video_player:
            self._video_player.load_video(video_path)

    def display_error(self, message: str) -> None:
        QMessageBox.critical(self, "Error", message)

    def on_component_error(self, message: str) -> None:
        with contextlib.suppress(Exception):
            logging.error(message)
        self.display_error(message)

    def update_window_data(self, window_data: list[WindowDataEntry]) -> None:
        if self._timeline:
            self._timeline.load_window_data(window_data)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)


def main() -> None:
    parser = argparse.ArgumentParser(description="Activity Beacon")
    parser.add_argument(
        "--base-dir",
        "-b",
        help="Base screenshots directory",
        default=str(Path.home() / "Documents" / "Screenshots"),
    )
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setApplicationName("Activity Beacon")
    with contextlib.suppress(Exception):
        app.setWindowIcon(
            QApplication.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        )

    log_dir = Path.home() / ".logs" / "activity_beacon"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"viewer_{datetime.now().strftime("%Y%m%d")}.log"
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    fh = logging.FileHandler(str(log_file))
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    base_path = Path(args.base_dir)
    if not base_path.exists() or not base_path.is_dir():
        logging.error("Screenshots directory not found: %s", base_path)
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Error")
        msg.setText("Screenshots directory not found")
        msg.setInformativeText(str(base_path))
        msg.exec()
        sys.exit(2)

    w = MainWindow(base_dir=base_path)
    w.show()
    rc = app.exec()
    sys.exit(rc)


if __name__ == "__main__":
    main()
