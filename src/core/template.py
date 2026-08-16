"""Watermark text template generation and font resolution utilities."""

import os
from typing import Dict, List
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


class TemplateRenderer:
    """Renders binary watermark text templates at variable target heights with caching."""

    DEFAULT_TEXT: str = "NotebookLM"

    # Known standard sans-serif font candidates across platforms
    FONT_CANDIDATES: List[str] = [
        # Windows
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        # Linux (Debian, Ubuntu, Fedora, RHEL, Arch)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "/usr/share/fonts/msttcore/arial.ttf",
        # macOS
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]

    def __init__(self, text: str = DEFAULT_TEXT):
        self.text = text
        self._cache: Dict[int, np.ndarray] = {}

    def _resolve_font(self, font_size: int) -> ImageFont.ImageFont:
        """Finds the best available TrueType font or falls back to PIL default font."""
        for path in self.FONT_CANDIDATES:
            if os.path.isfile(path):
                try:
                    return ImageFont.truetype(path, font_size)
                except Exception:
                    continue
        return ImageFont.load_default()

    def render_template(self, height: int) -> np.ndarray:
        """
        Creates a cropped binary template for the watermark text at a given target height.
        
        Args:
            height: Desired height in pixels.
            
        Returns:
            A 2D binary uint8 numpy array with text pixels as foreground (255).
        """
        key = max(10, int(height))
        if key in self._cache:
            return self._cache[key]

        font_size = max(12, int(key * 1.15))
        canvas_w = max(180, font_size * 14)
        canvas_h = max(40, font_size * 3)

        img = Image.new('L', (canvas_w, canvas_h), 255)
        draw = ImageDraw.Draw(img)
        font = self._resolve_font(font_size)

        bbox = draw.textbbox((0, 0), self.text, font=font)
        th = bbox[3] - bbox[1]
        x = 8
        y = max(4, (canvas_h - th) // 2 - bbox[1])
        draw.text((x, y), self.text, fill=0, font=font)

        arr = np.array(img)
        _, binary = cv2.threshold(arr, 200, 255, cv2.THRESH_BINARY_INV)
        ys, xs = np.where(binary > 0)

        if len(xs) == 0 or len(ys) == 0:
            tpl = np.zeros((10, 80), dtype=np.uint8)
        else:
            tpl = binary[ys.min():ys.max() + 1, xs.min():xs.max() + 1]

        self._cache[key] = tpl
        return tpl
