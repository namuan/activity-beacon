import numpy as np
from PIL import Image

from activity_beacon.logging import get_logger

logger = get_logger("activity_beacon.screenshot")

DEFAULT_THRESHOLD = 10


class ChangeDetector:
    """Detects pixel-level changes between consecutive screenshots."""

    def __init__(  # type: ignore[no-untyped-def]
        self, threshold: int = DEFAULT_THRESHOLD
    ) -> None:
        """Initialize the change detector.

        Args:
            threshold: Minimum pixel difference to consider as a change (0-255).
                      Default is 10.
        """
        self.threshold = threshold
        self.last_error_msg: str | None = None
        logger.debug(f"ChangeDetector initialized with threshold={threshold}")

    def has_changed(
        self, previous_image: Image.Image | None, current_image: Image.Image
    ) -> bool:
        """Check if the current image has changed from the previous image.

        Args:
            previous_image: The previous screenshot image, or None if first capture.
            current_image: The current screenshot image.

        Returns:
            True if images are different beyond threshold, False otherwise.
            Returns True if previous_image is None (first capture).
        """
        if previous_image is None:
            logger.debug("No previous image, considering as changed")
            return True

        try:
            # Ensure images are the same size
            if previous_image.size != current_image.size:
                logger.debug(
                    f"Image size mismatch: {previous_image.size} vs {current_image.size}"
                )
                return True

            # Convert images to numpy arrays
            prev_array = np.array(previous_image)
            curr_array = np.array(current_image)

            # Calculate absolute pixel differences
            diff = np.abs(curr_array.astype(np.int16) - prev_array.astype(np.int16))

            # Check if any pixel difference exceeds threshold
            max_diff_value = np.max(diff)  # type: ignore[reportAny]
            max_diff: int = int(max_diff_value)  # type: ignore[reportAny]
            changed: bool = max_diff > self.threshold

            logger.debug(
                f"Image comparison: max_diff={max_diff}, threshold={self.threshold}, changed={changed}"
            )
            return changed

        except (ValueError, TypeError, AttributeError) as e:
            self.last_error_msg = str(e)
            logger.error(f"Failed to compare images: {e}")
            # On error, assume changed to avoid missing captures
            return True

    def calculate_difference_percentage(
        self, previous_image: Image.Image, current_image: Image.Image
    ) -> float:
        """Calculate the percentage of pixels that changed.

        Args:
            previous_image: The previous screenshot image.
            current_image: The current screenshot image.

        Returns:
            Percentage of pixels that changed (0-100).
        """
        if previous_image.size != current_image.size:
            msg = f"Image size mismatch: {previous_image.size} vs {current_image.size}"
            logger.error(msg)
            self.last_error_msg = msg
            raise ValueError(msg)

        try:
            # Convert images to numpy arrays
            prev_array = np.array(previous_image)
            curr_array = np.array(current_image)

            # Calculate absolute pixel differences
            diff = np.abs(curr_array.astype(np.int16) - prev_array.astype(np.int16))

            # Count pixels that changed beyond threshold
            changed_pixels = np.sum(diff > self.threshold)
            total_pixels = diff.size

            percentage = (changed_pixels / total_pixels) * 100
            logger.debug(
                f"Difference: {changed_pixels}/{total_pixels} pixels ({percentage:.2f}%)"
            )
            return float(percentage)

        except (ValueError, TypeError, AttributeError) as e:
            self.last_error_msg = str(e)
            logger.error(f"Failed to calculate difference percentage: {e}")
            raise
