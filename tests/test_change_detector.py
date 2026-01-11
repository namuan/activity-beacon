import numpy as np
from PIL import Image
import pytest

from activity_beacon.screenshot.change_detector import ChangeDetector


def create_test_image(
    width: int, height: int, color: tuple[int, int, int]
) -> Image.Image:
    """Create a test image with solid color."""
    return Image.new("RGB", (width, height), color)


def create_gradient_image(width: int, height: int) -> Image.Image:
    """Create a test image with gradient."""
    arr = np.zeros((height, width, 3), dtype=np.uint8)
    for i in range(height):
        arr[i, :, 0] = int(255 * i / height)
    return Image.fromarray(arr)


class TestChangeDetector:
    def test_default_threshold(self) -> None:
        """Test that default threshold is 10."""
        detector = ChangeDetector()
        assert detector.threshold == 10

    def test_custom_threshold(self) -> None:
        """Test custom threshold initialization."""
        detector = ChangeDetector(threshold=25)
        assert detector.threshold == 25

    def test_no_previous_image_returns_true(self) -> None:
        """Test that first capture (no previous image) returns True."""
        detector = ChangeDetector()
        current = create_test_image(100, 100, (255, 0, 0))

        result = detector.has_changed(None, current)

        assert result is True

    def test_identical_images_returns_false(self) -> None:
        """Test that identical images return False."""
        detector = ChangeDetector()
        image1 = create_test_image(100, 100, (255, 0, 0))
        image2 = create_test_image(100, 100, (255, 0, 0))

        result = detector.has_changed(image1, image2)

        assert result is False

    def test_completely_different_images_returns_true(self) -> None:
        """Test that completely different images return True."""
        detector = ChangeDetector()
        image1 = create_test_image(100, 100, (0, 0, 0))
        image2 = create_test_image(100, 100, (255, 255, 255))

        result = detector.has_changed(image1, image2)

        assert result is True

    def test_small_change_below_threshold(self) -> None:
        """Test that small changes below threshold return False."""
        detector = ChangeDetector(threshold=10)
        image1 = create_test_image(100, 100, (100, 100, 100))
        # Change by 5 (below threshold of 10)
        image2 = create_test_image(100, 100, (105, 105, 105))

        result = detector.has_changed(image1, image2)

        assert result is False

    def test_change_at_threshold_boundary(self) -> None:
        """Test that change exactly at threshold returns False."""
        detector = ChangeDetector(threshold=10)
        image1 = create_test_image(100, 100, (100, 100, 100))
        # Change by exactly 10
        image2 = create_test_image(100, 100, (110, 110, 110))

        result = detector.has_changed(image1, image2)

        assert result is False

    def test_change_above_threshold_returns_true(self) -> None:
        """Test that change above threshold returns True."""
        detector = ChangeDetector(threshold=10)
        image1 = create_test_image(100, 100, (100, 100, 100))
        # Change by 11 (above threshold of 10)
        image2 = create_test_image(100, 100, (111, 111, 111))

        result = detector.has_changed(image1, image2)

        assert result is True

    def test_size_mismatch_returns_true(self) -> None:
        """Test that different sized images return True."""
        detector = ChangeDetector()
        image1 = create_test_image(100, 100, (255, 0, 0))
        image2 = create_test_image(200, 200, (255, 0, 0))

        result = detector.has_changed(image1, image2)

        assert result is True

    def test_single_pixel_change_detected(self) -> None:
        """Test that a single pixel change above threshold is detected."""
        detector = ChangeDetector(threshold=10)

        # Create images with one pixel different
        arr1 = np.zeros((100, 100, 3), dtype=np.uint8)
        arr2 = np.zeros((100, 100, 3), dtype=np.uint8)
        arr2[50, 50] = [255, 255, 255]  # One bright pixel

        image1 = Image.fromarray(arr1)
        image2 = Image.fromarray(arr2)

        result = detector.has_changed(image1, image2)

        assert result is True

    def test_calculate_difference_percentage_identical(self) -> None:
        """Test difference percentage for identical images is 0."""
        detector = ChangeDetector()
        image1 = create_test_image(100, 100, (255, 0, 0))
        image2 = create_test_image(100, 100, (255, 0, 0))

        percentage = detector.calculate_difference_percentage(image1, image2)

        assert percentage == 0.0

    def test_calculate_difference_percentage_complete_change(self) -> None:
        """Test difference percentage for completely different images."""
        detector = ChangeDetector(threshold=10)
        image1 = create_test_image(100, 100, (0, 0, 0))
        image2 = create_test_image(100, 100, (255, 255, 255))

        percentage = detector.calculate_difference_percentage(image1, image2)

        # All pixels should be detected as changed (3 channels per pixel)
        assert percentage == pytest.approx(100.0, abs=0.1)

    def test_calculate_difference_percentage_partial_change(self) -> None:
        """Test difference percentage for partial image change."""
        detector = ChangeDetector(threshold=10)

        # Create images where half the pixels change
        arr1 = np.zeros((100, 100, 3), dtype=np.uint8)
        arr2 = np.zeros((100, 100, 3), dtype=np.uint8)
        arr2[:50, :] = [255, 255, 255]  # Top half is white

        image1 = Image.fromarray(arr1)
        image2 = Image.fromarray(arr2)

        percentage = detector.calculate_difference_percentage(image1, image2)

        # 50% of pixels changed
        assert percentage == pytest.approx(50.0, abs=1.0)

    def test_calculate_difference_percentage_size_mismatch_raises(self) -> None:
        """Test that size mismatch raises ValueError."""
        detector = ChangeDetector()
        image1 = create_test_image(100, 100, (255, 0, 0))
        image2 = create_test_image(200, 200, (255, 0, 0))

        with pytest.raises(ValueError, match="Image size mismatch"):
            detector.calculate_difference_percentage(image1, image2)

    def test_threshold_zero_detects_any_change(self) -> None:
        """Test that threshold of 0 detects any pixel change."""
        detector = ChangeDetector(threshold=0)
        image1 = create_test_image(100, 100, (100, 100, 100))
        # Change by 1
        image2 = create_test_image(100, 100, (101, 101, 101))

        result = detector.has_changed(image1, image2)

        assert result is True

    def test_high_threshold_ignores_moderate_changes(self) -> None:
        """Test that high threshold ignores moderate changes."""
        detector = ChangeDetector(threshold=100)
        image1 = create_test_image(100, 100, (100, 100, 100))
        # Change by 50 (below threshold of 100)
        image2 = create_test_image(100, 100, (150, 150, 150))

        result = detector.has_changed(image1, image2)

        assert result is False

    def test_gradient_images_detection(self) -> None:
        """Test change detection with gradient images."""
        detector = ChangeDetector(threshold=10)
        image1 = create_gradient_image(100, 100)
        image2 = create_gradient_image(100, 100)

        # Same gradient should be detected as no change
        result = detector.has_changed(image1, image2)
        assert result is False

    def test_composite_image_support(self) -> None:
        """Test that detector works with composite (stitched) images."""
        detector = ChangeDetector()

        # Create a wide composite-like image
        image1 = create_test_image(3840, 1080, (100, 100, 100))
        image2 = create_test_image(3840, 1080, (200, 200, 200))

        result = detector.has_changed(image1, image2)

        assert result is True

    def test_error_handling_sets_last_error_msg(self) -> None:
        """Test that errors are captured in last_error_msg."""
        detector = ChangeDetector()
        image1 = create_test_image(100, 100, (255, 0, 0))
        image2 = create_test_image(200, 200, (255, 0, 0))

        with pytest.raises(ValueError):
            detector.calculate_difference_percentage(image1, image2)

        assert detector.last_error_msg is not None
        assert "Image size mismatch" in detector.last_error_msg

    def test_different_color_channels(self) -> None:
        """Test detection of changes in different color channels."""
        detector = ChangeDetector(threshold=10)

        # Red channel changes
        image1 = create_test_image(100, 100, (100, 50, 50))
        image2 = create_test_image(100, 100, (150, 50, 50))
        assert detector.has_changed(image1, image2) is True

        # Green channel changes
        image1 = create_test_image(100, 100, (50, 100, 50))
        image2 = create_test_image(100, 100, (50, 150, 50))
        assert detector.has_changed(image1, image2) is True

        # Blue channel changes
        image1 = create_test_image(100, 100, (50, 50, 100))
        image2 = create_test_image(100, 100, (50, 50, 150))
        assert detector.has_changed(image1, image2) is True
