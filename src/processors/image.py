"""Image format processor for PNG, JPG, JPEG, and WEBP files."""

import logging
from typing import Optional, Tuple
import cv2
import numpy as np

from processors.base import BaseProcessor

logger = logging.getLogger(__name__)


class ImageProcessor(BaseProcessor):
    """Processes standalone images (PNG with alpha, JPG, JPEG, WEBP)."""

    @property
    def supported_extensions(self) -> Tuple[str, ...]:
        return ('.png', '.jpg', '.jpeg', '.webp')

    def clean_roi_scaled(self, roi_bgr: np.ndarray) -> Optional[np.ndarray]:
        """
        Upscales the bottom-right ROI for sub-pixel accuracy detection/healing,
        then maps only the active watermark mask back onto the original resolution image.
        """
        scale = self.config.pdf_dpi_scale
        h, w = roi_bgr.shape[:2]
        roi_hr = cv2.resize(roi_bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)

        result = self.reconstructor.clean_roi(roi_hr)
        if result is None:
            return None
        cleaned_hr, mask_hr = result

        cleaned = cv2.resize(cleaned_hr, (w, h), interpolation=cv2.INTER_LINEAR)
        mask = cv2.resize(mask_hr, (w, h), interpolation=cv2.INTER_NEAREST)

        out = roi_bgr.copy()
        out[mask > 0] = cleaned[mask > 0]
        return out

    def process(self, input_path: str, output_path: str, **kwargs) -> bool:
        """Removes watermark from a single image file."""
        try:
            img = cv2.imread(input_path, cv2.IMREAD_UNCHANGED)
            if img is None:
                logger.error(f"Could not read image: {input_path}")
                return False

            h, w = img.shape[:2]
            has_alpha = len(img.shape) == 3 and img.shape[2] == 4

            if has_alpha:
                channels = cv2.split(img)
                img_bgr = cv2.merge(channels[:3])
                alpha = channels[3]
            else:
                img_bgr = img.copy()
                alpha = None

            mx, my = self.config.search_margin_x, self.config.search_margin_y
            y0 = max(0, h - my)
            x0 = max(0, w - mx)

            roi = img_bgr[y0:h, x0:w].copy()
            cleaned_roi = self.clean_roi_scaled(roi)

            if cleaned_roi is None:
                logger.warning(f"No watermark detected in {input_path}")
                return False

            img_bgr[y0:h, x0:w] = cleaned_roi
            img_final = cv2.merge([*cv2.split(img_bgr), alpha]) if has_alpha else img_bgr

            cv2.imwrite(output_path, img_final)
            self.last_stats = {'patched': 1, 'total': 1, 'unit': 'image'}
            logger.info(f"Saved cleaned image to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error processing image {input_path}: {e}")
            return False
