"""Watermark detection, component analysis, and mask generation."""

import os
import logging
from typing import Optional, List, Tuple
import cv2
import numpy as np

from config import WatermarkConfig
from core.template import TemplateRenderer

logger = logging.getLogger(__name__)


class WatermarkDetector:
    """Detects NotebookLM watermark text and icons within an image ROI and produces a mask."""

    def __init__(self, config: Optional[WatermarkConfig] = None, template_renderer: Optional[TemplateRenderer] = None):
        self.config = config or WatermarkConfig()
        self.template_renderer = template_renderer or TemplateRenderer()

    def debug_save(self, name: str, img: np.ndarray) -> None:
        """Saves intermediate debug images if debug mode is active."""
        if not self.config.debug:
            return
        try:
            os.makedirs("debug_watermark", exist_ok=True)
            cv2.imwrite(os.path.join("debug_watermark", name), img)
        except Exception as e:
            logger.debug(f"Failed to save debug image {name}: {e}")

    def is_light_background(self, gray: np.ndarray) -> bool:
        """
        Determines the overall polarity of the background by sampling the border ring of the ROI.
        Returns True for a light background with dark text, False for a dark background with light text.
        """
        h, w = gray.shape[:2]
        border = max(2, min(h, w) // 20)
        edge_pixels = np.concatenate([
            gray[:border, :].ravel(),
            gray[-border:, :].ravel(),
            gray[:, :border].ravel(),
            gray[:, -border:].ravel(),
        ])
        return float(np.median(edge_pixels)) >= 128

    def match_template_text(self, roi_bgr: np.ndarray) -> Tuple[Optional[Tuple[int, int, int, int]], float]:
        """
        Matches multi-scale text templates against the grayscale equalized ROI.
        
        Returns:
            ((x, y, w, h), best_score) if matched above threshold, else (None, best_score).
        """
        h, w = roi_bgr.shape[:2]
        if h < 20 or w < 80:
            return None, 0.0

        gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
        light_bg = self.is_light_background(gray)
        gray_eq = cv2.equalizeHist(gray)

        best_score = 0.0
        best_box: Optional[Tuple[int, int, int, int]] = None

        min_h = max(14, h // 5)
        max_h = max(18, min(h - 2, h // 2 + 20))

        for text_h in range(min_h, max_h, 3):
            tpl = self.template_renderer.render_template(text_h)
            th, tw = tpl.shape[:2]
            if th >= h or tw >= w:
                continue

            result = cv2.matchTemplate(gray_eq, tpl, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

            # Check correlation sign matching polarity
            if light_bg:
                match_val, match_loc = -min_val, min_loc
            else:
                match_val, match_loc = max_val, max_loc

            if match_val > best_score:
                x, y = match_loc
                best_score = float(match_val)
                best_box = (x, y, tw, th)

        if best_score < self.config.text_match_threshold:
            return None, best_score

        return best_box, best_score

    def extract_candidates(self, roi_bgr: np.ndarray) -> np.ndarray:
        """
        Extracts high-contrast candidate watermark strokes and glyphs using local background estimation.
        """
        gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
        light_bg = self.is_light_background(gray)

        ksize = max(15, min(41, ((min(gray.shape[:2]) // 5) | 1)))
        bg = cv2.medianBlur(gray, ksize)

        if light_bg:
            diff = cv2.subtract(bg, gray)
            luma_mask = np.where(gray < self.config.text_luma_threshold, 255, 0).astype(np.uint8)
        else:
            diff = cv2.subtract(gray, bg)
            luma_mask = np.where(gray > (255 - self.config.text_luma_threshold), 255, 0).astype(np.uint8)

        _, diff_mask = cv2.threshold(diff, self.config.pixel_threshold, 255, cv2.THRESH_BINARY)
        mask = cv2.bitwise_and(luma_mask, diff_mask)

        # Restrict to bottom-right region of ROI
        h, w = gray.shape[:2]
        geom = np.zeros_like(mask)
        x0 = int(w * self.config.roi_right_bias)
        y0 = int(h * self.config.roi_bottom_bias)
        geom[y0:h, x0:w] = 255
        mask = cv2.bitwise_and(mask, geom)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=self.config.close_iterations)
        mask = cv2.dilate(mask, kernel, iterations=self.config.dilate_iterations)
        return mask

    def component_boxes_from_mask(self, mask: np.ndarray) -> List[Tuple[int, int, int, int, int]]:
        """Finds filtered connected component bounding boxes from a binary mask."""
        n, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        h, w = mask.shape[:2]
        out: List[Tuple[int, int, int, int, int]] = []

        for i in range(1, n):
            x, y, cw, ch, area = stats[i]
            if area < self.config.min_component_area:
                continue
            if area > int(h * w * self.config.max_component_area_ratio):
                continue
            out.append((int(x), int(y), int(cw), int(ch), int(area)))

        return out

    def find_icon_component(
        self,
        comps: List[Tuple[int, int, int, int, int]],
        text_box: Tuple[int, int, int, int],
        roi_shape: Tuple[int, ...]
    ) -> Optional[Tuple[int, int, int, int]]:
        """Identifies any notebook icon glyph located adjacent to the left of the matched text."""
        tx, ty, _, th = text_box
        best = None
        best_score = -1e9
        _, w = roi_shape[:2]

        for x, y, cw, ch, area in comps:
            cx = x + cw / 2.0
            cy = y + ch / 2.0
            text_cy = ty + th / 2.0

            if cx >= tx:
                continue
            if abs(cy - text_cy) > max(18, th * 0.9):
                continue
            if cw > th * 1.8 or ch > th * 1.8:
                continue
            if x < w * 0.45:
                continue

            score = -abs((tx - (x + cw)) - max(4, th * 0.15)) - abs(ch - th * 0.65) + area * 0.02
            if score > best_score:
                best_score = score
                best = (x, y, cw, ch)

        return best

    def build_watermark_mask(self, roi_bgr: np.ndarray) -> Optional[np.ndarray]:
        """
        Hybrid watermark detection pipeline:
        1. Extract candidate contrast strokes.
        2. Detect text location via template matching.
        3. Fuse matched text with nearby icon glyphs.
        4. Apply morphological closing and dilation to form a tight, complete mask.
        """
        h, w = roi_bgr.shape[:2]
        if h < 10 or w < 20:
            return None

        candidate_mask = self.extract_candidates(roi_bgr)
        comps = self.component_boxes_from_mask(candidate_mask)
        if not comps:
            return None

        text_box, _ = self.match_template_text(roi_bgr)

        if text_box is None:
            # Fallback: analyze bottom-right connected components directly
            selected = []
            for x, y, cw, ch, area in comps:
                cx = x + cw / 2.0
                cy = y + ch / 2.0
                if cx < w * 0.60 or cy < h * 0.55:
                    continue
                if ch > h * 0.7 or cw > w * 0.8:
                    continue
                selected.append((x, y, cw, ch, area))

            if not selected:
                return None

            mask = np.zeros((h, w), dtype=np.uint8)
            n, labels, stats, _ = cv2.connectedComponentsWithStats(candidate_mask, connectivity=8)
            for i in range(1, n):
                x, y, cw, ch, area = stats[i]
                for sx, sy, sw, sh, sa in selected:
                    if x == sx and y == sy and cw == sw and ch == sh and area == sa:
                        mask[labels == i] = 255
                        break

            if cv2.countNonZero(mask) < self.config.min_watermark_area:
                return None

            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            mask = cv2.dilate(mask, kernel, iterations=2)
            self.debug_save("fallback_mask.png", mask)
            return mask

        tx, ty, tw, th = text_box
        pad = self.config.watermark_padding
        text_rect = (
            max(0, tx - pad),
            max(0, ty - pad),
            min(w, tx + tw + pad),
            min(h, ty + th + pad),
        )

        selected_mask = np.zeros((h, w), dtype=np.uint8)
        n, labels, stats, _ = cv2.connectedComponentsWithStats(candidate_mask, connectivity=8)

        for i in range(1, n):
            x, y, cw, ch, area = stats[i]
            if area < self.config.min_component_area:
                continue
            rx0, ry0, rx1, ry1 = text_rect
            overlaps = not (x + cw < rx0 or x > rx1 or y + ch < ry0 or y > ry1)
            near = (x <= rx1 + 14 and x + cw >= rx0 - 18 and y <= ry1 + 10 and y + ch >= ry0 - 10)
            if overlaps or near:
                selected_mask[labels == i] = 255

        icon_box = self.find_icon_component(comps, text_box, roi_bgr.shape)
        if icon_box is not None:
            ix, iy, iw, ih = icon_box
            for i in range(1, n):
                x, y, cw, ch, area = stats[i]
                if x == ix and y == iy and cw == iw and ch == ih:
                    selected_mask[labels == i] = 255

        # Ensure text band is filled if template matched but threshold missed minor pixels
        text_band = candidate_mask[max(0, ty - 3):min(h, ty + th + 3), max(0, tx - 4):min(w, tx + tw + 4)]
        if cv2.countNonZero(selected_mask) < self.config.min_watermark_area and cv2.countNonZero(text_band) > 40:
            selected_mask[max(0, ty - 3):min(h, ty + th + 3), max(0, tx - 4):min(w, tx + tw + 4)] = text_band

        if cv2.countNonZero(selected_mask) < self.config.min_watermark_area:
            return None

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        selected_mask = cv2.morphologyEx(selected_mask, cv2.MORPH_CLOSE, kernel, iterations=1)
        selected_mask = cv2.dilate(selected_mask, kernel, iterations=2)

        self.debug_save("candidate_mask.png", candidate_mask)
        self.debug_save("selected_mask.png", selected_mask)
        return selected_mask
