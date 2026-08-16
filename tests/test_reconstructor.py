"""Tests for patch-based background reconstruction and inpainting."""

import unittest
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from core.reconstructor import PatchReconstructor


class TestReconstructor(unittest.TestCase):

    def test_patch_reconstruct_empty_mask(self):
        reconstructor = PatchReconstructor()
        img = np.full((100, 200, 3), 128, dtype=np.uint8)
        mask = np.zeros((100, 200), dtype=np.uint8)
        result = reconstructor.patch_reconstruct(img, mask)
        np.testing.assert_array_equal(result, img)

    def test_patch_reconstruct_with_mask(self):
        reconstructor = PatchReconstructor()
        # Image with background color
        img = np.full((100, 300, 3), 200, dtype=np.uint8)
        # Mask in bottom right
        mask = np.zeros((100, 300), dtype=np.uint8)
        mask[70:90, 200:280] = 255
        # Add dark "watermark" inside mask
        img[70:90, 200:280] = 0

        cleaned = reconstructor.patch_reconstruct(img, mask)
        self.assertEqual(cleaned.shape, img.shape)
        # Reconstructed area should now be closer to background (200) than 0
        self.assertGreater(cleaned[75:85, 210:270].mean(), 150)


if __name__ == "__main__":
    unittest.main()
