import contextlib
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

MIN_ERROR_ARGS = 2


class VideoPlayerWidget(QWidget):
    position_changed = pyqtSignal(int)
    playback_state_changed = pyqtSignal(QMediaPlayer.PlaybackState)
    error_occurred = pyqtSignal(str)
    loading_changed = pyqtSignal(bool)

    def __init__(self) -> None:
        super().__init__()
        self._player = QMediaPlayer()
        self._audio = QAudioOutput()
        self._player.setAudioOutput(self._audio)
        self._video = QVideoWidget()
        self._player.setVideoOutput(self._video)
        self._video.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._video.setMinimumSize(320, 240)

        self._setup_widgets()
        self._setup_layout()
        self._setup_signals()

    def _setup_widgets(self) -> None:
        """Initialize UI widgets."""
        self._play_btn = QPushButton("Play")
        self._play_btn.setToolTip("Play/Pause video")
        self._position_slider = QSlider(Qt.Orientation.Horizontal)
        self._position_slider.setRange(0, 0)
        self._position_slider.setToolTip("Seek video position")
        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setRange(0, 100)
        self._volume_slider.setValue(50)
        self._volume_slider.setToolTip("Adjust playback volume")
        self._duration_label = QLabel("00:00")
        self._duration_label.setToolTip("Total duration")
        self._position_label = QLabel("00:00")
        self._position_label.setToolTip("Current playback position")
        self._status_label = QLabel()

    def _setup_layout(self) -> None:
        """Setup the layout."""
        top = QVBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(0)
        top.addWidget(self._video)
        self.setLayout(top)

        self._controls = QWidget()
        ctrl_v = QVBoxLayout()
        ctrl_v.setContentsMargins(0, 0, 0, 0)
        ctrl_v.setSpacing(8)
        ctrl = QHBoxLayout()
        ctrl.setContentsMargins(0, 0, 0, 0)
        ctrl.setSpacing(10)
        ctrl.addWidget(self._play_btn)
        ctrl.addWidget(self._position_label)
        ctrl.addWidget(self._position_slider)
        ctrl.addWidget(self._duration_label)
        ctrl.addWidget(QLabel("Vol"))
        ctrl.addWidget(self._volume_slider)
        ctrl_v.addLayout(ctrl)
        ctrl_v.addWidget(self._status_label)
        self._controls.setLayout(ctrl_v)

    def _setup_signals(self) -> None:
        """Setup signal connections."""
        self._play_btn.clicked.connect(self._toggle_play)
        self._position_slider.sliderMoved.connect(self._on_slider_moved)
        self._volume_slider.valueChanged.connect(self._on_volume_changed)

        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.playbackStateChanged.connect(self._on_playback_state_changed)
        self._player.mediaStatusChanged.connect(self._on_media_status_changed)
        with contextlib.suppress(AttributeError):
            self._player.errorOccurred.connect(self._on_error)

    def load_video(self, video_path: Path) -> None:
        if not video_path.exists() or not video_path.is_file():
            self._status_label.setText("Video not available")
            return
        self._status_label.setText("")
        self.loading_changed.emit(value=True)
        self._player.setSource(QUrl.fromLocalFile(str(video_path)))
        self._player.setPosition(0)
        self._position_slider.setValue(0)

    def play(self) -> None:
        self._player.play()

    def pause(self) -> None:
        self._player.pause()

    def seek(self, position_ms: int) -> None:
        self._player.setPosition(max(0, position_ms))

    def set_volume(self, volume: int) -> None:
        v = max(0, min(100, volume))
        self._audio.setVolume(v / 100.0)

    def get_duration(self) -> int:
        return int(self._player.duration())

    def get_position(self) -> int:
        return int(self._player.position())

    def _toggle_play(self) -> None:
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def _on_slider_moved(self, val: int) -> None:
        self._player.setPosition(val)

    def _on_volume_changed(self, val: int) -> None:
        self._audio.setVolume(val / 100.0)

    def _on_position_changed(self, pos: int) -> None:
        self._position_slider.blockSignals(block=True)
        self._position_slider.setValue(pos)
        self._position_slider.blockSignals(block=False)
        self.position_changed.emit(pos)
        self._position_label.setText(VideoPlayerWidget._fmt_ms(pos))

    def _on_duration_changed(self, dur: int) -> None:
        self._position_slider.setRange(0, dur)
        self._duration_label.setText(VideoPlayerWidget._fmt_ms(dur))

    def _on_playback_state_changed(self, st: QMediaPlayer.PlaybackState) -> None:
        self.playback_state_changed.emit(st)
        self._play_btn.setText(
            "Pause" if st == QMediaPlayer.PlaybackState.PlayingState else "Play"
        )

    @staticmethod
    def _fmt_ms(ms: int) -> str:
        s = max(0, int(ms // 1000))
        m = s // 60
        r = s % 60
        return f"{m:02d}:{r:02d}"

    def _on_media_status_changed(self, st: QMediaPlayer.MediaStatus) -> None:
        if st == QMediaPlayer.MediaStatus.EndOfMedia:
            self._player.pause()
            self._player.setPosition(0)
            self._position_slider.setValue(0)
        if st == QMediaPlayer.MediaStatus.InvalidMedia:
            msg = "Error loading video"
            self._status_label.setText(msg)
            self.error_occurred.emit(msg)
            self.loading_changed.emit(value=False)
        elif st == QMediaPlayer.MediaStatus.LoadingMedia:
            self.loading_changed.emit(value=True)
        elif st in {
            QMediaPlayer.MediaStatus.BufferedMedia,
            QMediaPlayer.MediaStatus.StalledMedia,
            QMediaPlayer.MediaStatus.LoadedMedia,
            QMediaPlayer.MediaStatus.NoMedia,
            QMediaPlayer.MediaStatus.BufferingMedia,
            QMediaPlayer.MediaStatus.BufferedMedia,
        }:
            self.loading_changed.emit(value=False)

    def _on_error(self, *args: str) -> None:
        msg = "Error loading video"
        if len(args) >= MIN_ERROR_ARGS and isinstance(args[1], str):
            msg = args[1]
        self._status_label.setText(msg)
        self.error_occurred.emit(msg)
        self.loading_changed.emit(value=False)

    def get_controls_widget(self) -> QWidget:
        return self._controls
