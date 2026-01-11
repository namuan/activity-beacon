from collections.abc import Mapping

from PIL import Image

from activity_beacon.logging import get_logger

logger = get_logger("activity_beacon.screenshot")


class ImageProcessor:
    def __init__(self) -> None:  # type: ignore[reportMissingSuperCall]
        self.last_error_msg: str | None = None

    @staticmethod
    def _calculate_scale_factor(
        source_width: int, source_height: int, target_width: int, target_height: int
    ) -> float:
        width_ratio = target_width / source_width
        height_ratio = target_height / source_height
        return min(width_ratio, height_ratio)

    @staticmethod
    def _find_target_resolution(images: dict[int, Image.Image]) -> tuple[int, int]:
        if not images:
            msg = "No images provided for stitching"
            logger.error(msg)
            raise ValueError(msg)

        max_area = 0
        target_width = 0
        target_height = 0

        for image in images.values():
            area = image.width * image.height
            if area > max_area:
                max_area = area
                target_width = image.width
                target_height = image.height

        logger.debug(f"Target resolution: {target_width}x{target_height}")
        return target_width, target_height

    def _scale_image(
        self, image: Image.Image, target_width: int, target_height: int
    ) -> Image.Image:
        source_width = image.width
        source_height = image.height

        scale_factor = self._calculate_scale_factor(
            source_width, source_height, target_width, target_height
        )

        new_width = int(source_width * scale_factor)
        new_height = int(source_height * scale_factor)

        logger.debug(
            f"Scaling image from {source_width}x{source_height} to {new_width}x{new_height}"
        )

        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def stitch_horizontally(self, images: dict[int, Image.Image]) -> Image.Image:
        if not images:
            msg = "Cannot stitch empty image collection"
            logger.error(msg)
            self.last_error_msg = msg
            raise ValueError(msg)

        try:
            target_width, target_height = self._find_target_resolution(images)

            scaled_images: list[Image.Image] = []
            total_width = 0
            max_height = 0

            for monitor_id in sorted(images.keys()):
                image = images[monitor_id]
                scaled = self._scale_image(image, target_width, target_height)
                scaled_images.append(scaled)
                total_width += scaled.width
                max_height = max(max_height, scaled.height)

            composite = Image.new("RGB", (total_width, max_height))

            x_offset = 0
            for scaled in scaled_images:
                composite.paste(scaled, (x_offset, 0))
                x_offset += scaled.width

            logger.info(
                f"Stitched {len(scaled_images)} images into {composite.width}x{composite.height}"
            )
            return composite

        except Exception as e:
            self.last_error_msg = str(e)
            logger.error(f"Failed to stitch images: {e}")
            raise

    def stitch_with_metadata(
        self,
        images: dict[int, Image.Image],
        metadata: Mapping[int, Mapping[str, object]],
    ) -> tuple[Image.Image, dict[str, object]]:
        composite = self.stitch_horizontally(images)

        stitch_metadata: dict[str, object] = {
            "source_monitors": list(images.keys()),
            "monitor_count": len(images),
            "composite_width": composite.width,
            "composite_height": composite.height,
            "monitor_metadata": metadata,
        }

        return composite, stitch_metadata
