"""Background reconstruction and texture-preserving patch healing."""

from typing import Optional, Tuple
import cv2
import numpy as np

from config import WatermarkConfig
from core.detector import WatermarkDetector


class PatchReconstructor:
    """Restores watermark regions using clean neighboring background patches or Telea inpainting."""

    def __init__(self, config: Optional[WatermarkConfig] = None, detector: Optional[WatermarkDetector] = None):
        self.config = config or WatermarkConfig()
        self.detector = detector or WatermarkDetector(self.config)

    def patch_reconstruct(self, img_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """
        Heals the masked watermark area by copying a nearby clean background patch.
        Preserves paper texture, grain, and gradients.
        
        Args:
            img_bgr: Source image ROI in BGR format.
            mask: Binary mask of watermark pixels (255 where watermark is present).
            
        Returns:
            Cleaned image ROI in BGR format.
        """
        if cv2.countNonZero(mask) == 0:
            return img_bgr

        h, w = mask.shape[:2]

        x0, y0, bw, bh = cv2.boundingRect(mask)

        # Expand slightly so the boundary comparison ring sits on clean pixels
        pad = 4
        x0_p = max(0, x0 - pad)
        y0_p = max(0, y0 - pad)
        x1_p = min(w, x0 + bw + pad)
        y1_p = min(h, y0 + bh + pad)

        bw_p = x1_p - x0_p
        bh_p = y1_p - y0_p

        dx = max(int(bw_p * 1.2), 24)
        dy = max(int(bh_p * 1.5), 24)
        offsets = [(-dx, 0), (dx, 0), (0, -dy), (0, dy), (-dx, -dy), (dx, -dy)]

        border = min(4, bh_p // 2, bw_p // 2)
        ring = np.zeros((bh_p, bw_p), dtype=bool)
        if border > 0:
            ring[:border, :] = ring[-border:, :] = True
            ring[:, :border] = ring[:, -border:] = True
        dest_ring = img_bgr[y0_p:y1_p, x0_p:x1_p][ring].astype(np.int16)

        best_patch = None
        best_diff = float('inf')

        for ddx, ddy in offsets:
            src_x = x0_p + ddx
            src_y = y0_p + ddy

            # Ensure donor patch is within image bounds and doesn't overlap watermark mask
            if src_x < 0 or src_y < 0 or src_x + bw_p > w or src_y + bh_p > h:
                continue
            src_mask = mask[src_y:src_y + bh_p, src_x:src_x + bw_p]
            if cv2.countNonZero(src_mask) != 0:
                continue

            candidate = img_bgr[src_y:src_y + bh_p, src_x:src_x + bw_p]
            if ring.any():
                diff = float(np.abs(candidate[ring].astype(np.int16) - dest_ring).mean())
            else:
                diff = 0.0

            if diff < best_diff:
                best_diff = diff
                best_patch = candidate.copy()

        out = img_bgr.copy()
        if best_patch is not None:
            target_roi = out[y0_p:y1_p, x0_p:x1_p]
            mask_roi = mask[y0_p:y1_p, x0_p:x1_p]

            # Alpha blending on mask edges for smooth seamless boundary transitions
            mask_float = mask_roi.astype(float) / 255.0
            mask_float = cv2.GaussianBlur(mask_float, (3, 3), 0)

            for c in range(3):
                target_roi[:, :, c] = (
                    target_roi[:, :, c] * (1 - mask_float) +
                    best_patch[:, :, c] * mask_float
                ).astype(np.uint8)
        else:
            # Fallback to standard Telea inpainting if no clean donor patch fits
            out = cv2.inpaint(out, mask, self.config.inpaint_radius, cv2.INPAINT_TELEA)

        return out

    def clean_roi(self, roi_bgr: np.ndarray) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        Builds a watermark mask for the given ROI and restores the background.
        
        Returns:
            (cleaned_bgr_roi, mask) if watermark was found and removed, or None.
        """
        mask = self.detector.build_watermark_mask(roi_bgr)
        if mask is None:
            return None

        if self.config.use_patch_heal:
            cleaned = self.patch_reconstruct(roi_bgr, mask)
        else:
            cleaned = cv2.inpaint(roi_bgr, mask, self.config.inpaint_radius, cv2.INPAINT_TELEA)

        return cleaned, mask
