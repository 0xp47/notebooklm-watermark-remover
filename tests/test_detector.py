"""Tests for watermark detection algorithms and polarity checks."""

import unittest
import sys
from pathlib import Path
import numpy as np
import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from core.detector import WatermarkDetector


class TestDetector(unittest.TestCase):

    def test_is_light_background(self):
        detector = WatermarkDetector()
        light_img = np.full((100, 100), 240, dtype=np.uint8)
        self.assertTrue(detector.is_light_background(light_img))

        dark_img = np.full((100, 100), 20, dtype=np.uint8)
        self.assertFalse(detector.is_light_background(dark_img))

    def test_extract_candidates_empty(self):
        detector = WatermarkDetector()
        roi = np.full((100, 200, 3), 255, dtype=np.uint8)
        mask = detector.extract_candidates(roi)
        self.assertIsInstance(mask, np.ndarray)
        self.assertEqual(cv2.countNonZero(mask), 0)

    def test_build_watermark_mask_blank(self):
        detector = WatermarkDetector()
        blank_roi = np.full((100, 300, 3), 255, dtype=np.uint8)
        mask = detector.build_watermark_mask(blank_roi)
        self.assertIsNone(mask)


if __name__ == "__main__":
    unittest.main()
