from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class WindowInfo:
    window_name: str
    app_name: str
    pid: int
    is_focused: bool
    screen_rect: tuple[int, int, int, int]


@dataclass(frozen=True)
class FocusedAppData:
    app_name: str
    pid: int
    window_name: str | None
    timestamp: datetime

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            object.__setattr__(self, "timestamp", self.timestamp.replace(tzinfo=None))


@dataclass(frozen=True)
class WindowDataEntry:
    timestamp: datetime
    focused_app: FocusedAppData
    all_windows: tuple[WindowInfo, ...]
    screenshot_path: str | None

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            object.__setattr__(self, "timestamp", self.timestamp.replace(tzinfo=None))
