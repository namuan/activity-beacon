from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import mss
from mss.base import MSSBase
from PIL import Image

from activity_beacon.logging import get_logger

logger = get_logger("activity_beacon.screenshot")


@dataclass(frozen=True)
class MonitorInfo:
    monitor_id: int
    name: str
    x: int
    y: int
    width: int
    height: int
    is_primary: bool

    @property
    def geometry(self) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.width, self.height)

    @property
    def resolution(self) -> tuple[int, int]:
        return (self.width, self.height)


class ScreenshotCapture:
    def __init__(self) -> None:  # type: ignore[no-untyped-def]
        self._mss: MSSBase | None = None
        self._monitors: list[MonitorInfo] = []
        self.last_error_msg: str | None = None

    def _ensure_mss(self) -> MSSBase:
        if self._mss is None:
            self._mss = mss.mss()
        return self._mss

    def enumerate_monitors(self) -> list[MonitorInfo]:
        sct = self._ensure_mss()
        self._monitors = []
        primary_x: int = 0
        primary_y: int = 0

        for i, monitor in enumerate(sct.monitors):
            if i == 0:
                continue

            is_primary: bool = (
                monitor["left"] == primary_x and monitor["top"] == primary_y
            )

            monitor_info = MonitorInfo(
                monitor_id=i,
                name=f"Monitor {i}",
                x=monitor["left"],
                y=monitor["top"],
                width=monitor["width"],
                height=monitor["height"],
                is_primary=is_primary,
            )
            self._monitors.append(monitor_info)
            logger.debug(
                f"Detected monitor {i}: {monitor_info.resolution} at ({monitor_info.x}, {monitor_info.y})"
            )

        logger.info(f"Enumerated {len(self._monitors)} monitor(s)")
        return self._monitors

    def get_monitor_count(self) -> int:
        if not self._monitors:
            self.enumerate_monitors()
        return len(self._monitors)

    def get_monitor_info(self, monitor_id: int) -> MonitorInfo | None:
        if not self._monitors:
            self.enumerate_monitors()

        for monitor in self._monitors:
            if monitor.monitor_id == monitor_id:
                return monitor
        return None

    def capture_monitor(self, monitor_id: int) -> Image.Image:
        sct = self._ensure_mss()
        monitor_info = self.get_monitor_info(monitor_id)

        if monitor_info is None:
            msg = f"Monitor {monitor_id} not found"
            logger.error(msg)
            raise ValueError(msg)

        monitor_geometry = {
            "left": monitor_info.x,
            "top": monitor_info.y,
            "width": monitor_info.width,
            "height": monitor_info.height,
        }

        logger.debug(f"Capturing monitor {monitor_id}: {monitor_geometry}")
        sct_img = sct.grab(monitor_geometry)
        return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

    def capture_all_monitors(self) -> dict[int, Image.Image]:
        if not self._monitors:
            self.enumerate_monitors()

        captures: dict[int, Image.Image] = {}
        for monitor in self._monitors:
            captures[monitor.monitor_id] = self.capture_monitor(monitor.monitor_id)

        logger.info(f"Captured {len(captures)} monitor(s)")
        return captures

    def capture_to_path(
        self,
        monitor_id: int,
        output_path: Path,
        format: Literal["PNG", "JPEG", "BMP"] = "PNG",
    ) -> Path:
        try:
            image = self.capture_monitor(monitor_id)
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            image_format = format.upper()
            if image_format == "JPEG":
                image = image.convert("RGB")

            image.save(output_path, format=image_format)
            logger.info(f"Saved screenshot to {output_path}")
            return output_path
        except PermissionError as e:
            error_msg = f"Permission denied writing to {output_path}: {e}"
            logger.error(error_msg)
            self.last_error_msg = error_msg
            raise OSError(error_msg) from e
        except OSError as e:
            error_msg = f"Failed to write screenshot to {output_path}: {e}"
            logger.error(error_msg)
            self.last_error_msg = error_msg
            raise OSError(error_msg) from e

    def close(self) -> None:
        if self._mss is not None:
            try:
                self._mss.close()
                self._mss = None
                logger.debug("Closed MSS connection")
            except OSError as e:
                error_msg = f"Error closing MSS connection: {e}"
                logger.error(error_msg)
                self.last_error_msg = error_msg

    def __enter__(self) -> "ScreenshotCapture":
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()
