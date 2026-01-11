from PIL import Image
import pytest

from activity_beacon.screenshot.image_processor import ImageProcessor


def create_test_image(
    width: int, height: int, color: tuple[int, int, int]
) -> Image.Image:
    return Image.new("RGB", (width, height), color)


class TestImageProcessor:
    def test_stitch_empty_images(self) -> None:
        processor = ImageProcessor()
        with pytest.raises(ValueError, match="Cannot stitch empty image collection"):
            processor.stitch_horizontally({})

    def test_stitch_single_image(self) -> None:
        processor = ImageProcessor()
        image = create_test_image(1920, 1080, (255, 0, 0))

        result = processor.stitch_horizontally({1: image})

        assert result.width == 1920
        assert result.height == 1080

    def test_stitch_two_same_resolution(self) -> None:
        processor = ImageProcessor()

        image1 = create_test_image(1920, 1080, (255, 0, 0))
        image2 = create_test_image(1920, 1080, (0, 255, 0))

        result = processor.stitch_horizontally({1: image1, 2: image2})

        assert result.width == 3840
        assert result.height == 1080

    def test_stitch_two_different_resolution_smaller_scaled(self) -> None:
        processor = ImageProcessor()

        image1 = create_test_image(1920, 1080, (255, 0, 0))
        image2 = create_test_image(2560, 1440, (0, 255, 0))

        result = processor.stitch_horizontally({1: image1, 2: image2})

        assert result.width == 5120
        assert result.height == 1440

    def test_stitch_three_monitors_different_resolutions(self) -> None:
        processor = ImageProcessor()

        image1 = create_test_image(1920, 1080, (255, 0, 0))
        image2 = create_test_image(2560, 1440, (0, 255, 0))
        image3 = create_test_image(1280, 720, (0, 0, 255))

        result = processor.stitch_horizontally({1: image1, 2: image2, 3: image3})

        assert result.width == 7680
        assert result.height == 1440

    def test_stitch_preserves_aspect_ratio(self) -> None:
        processor = ImageProcessor()

        image1 = create_test_image(1920, 1080, (255, 0, 0))
        image2 = create_test_image(3840, 2160, (0, 255, 0))

        result = processor.stitch_horizontally({1: image1, 2: image2})

        assert result.width == 7680
        assert result.height == 2160

    def test_stitch_uses_lanczos_resampling(self) -> None:
        processor = ImageProcessor()

        image1 = create_test_image(1920, 1080, (255, 0, 0))
        image2 = create_test_image(1920, 1080, (0, 255, 0))

        result = processor.stitch_horizontally({1: image1, 2: image2})

        assert result.width == 3840
        assert result.height == 1080

    def test_stitch_monitor_order(self) -> None:
        processor = ImageProcessor()

        image1 = create_test_image(1920, 1080, (255, 0, 0))
        image2 = create_test_image(1920, 1080, (0, 255, 0))
        image3 = create_test_image(1920, 1080, (0, 0, 255))

        result = processor.stitch_horizontally({3: image3, 1: image1, 2: image2})

        assert result.width == 5760
        assert result.height == 1080

    def test_stitch_with_metadata(self) -> None:
        processor = ImageProcessor()

        image1 = create_test_image(1920, 1080, (255, 0, 0))
        image2 = create_test_image(1920, 1080, (0, 255, 0))

        metadata: dict[int, dict[str, object]] = {
            1: {"is_primary": True},
            2: {"is_primary": False},
        }

        _, stitch_metadata = processor.stitch_with_metadata(
            {1: image1, 2: image2}, metadata
        )

        assert "source_monitors" in stitch_metadata
        assert "monitor_count" in stitch_metadata
        assert "composite_width" in stitch_metadata
        assert "composite_height" in stitch_metadata
        assert "monitor_metadata" in stitch_metadata
        assert stitch_metadata["monitor_count"] == 2
        assert stitch_metadata["monitor_metadata"] == metadata

    def test_calculate_scale_factor_equal(self) -> None:
        processor = ImageProcessor()
        scale = processor._calculate_scale_factor(1920, 1080, 1920, 1080)
        assert scale == 1.0

    def test_calculate_scale_factor_width_constrained(self) -> None:
        processor = ImageProcessor()
        scale = processor._calculate_scale_factor(1920, 1080, 960, 1080)
        assert scale == 0.5

    def test_calculate_scale_factor_height_constrained(self) -> None:
        processor = ImageProcessor()
        scale = processor._calculate_scale_factor(1920, 1080, 1920, 540)
        assert scale == 0.5

    def test_calculate_scale_factor_maintains_aspect(self) -> None:
        processor = ImageProcessor()
        scale = processor._calculate_scale_factor(1920, 1080, 3840, 2160)
        assert scale == 2.0

    def test_last_error_msg_is_none_on_success(self) -> None:
        processor = ImageProcessor()
        image = Image.new("RGB", (1920, 1080), (255, 0, 0))

        processor.stitch_horizontally({1: image})

        assert processor.last_error_msg is None
