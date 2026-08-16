"""Tests for configuration dataclasses and validation."""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import WatermarkConfig


class TestConfig(unittest.TestCase):

    def test_default_config(self):
        config = WatermarkConfig()
        self.assertEqual(config.search_margin_x, 400)
        self.assertEqual(config.search_margin_y, 120)
        self.assertEqual(config.watermark_padding, 6)
        self.assertEqual(config.pixel_threshold, 22)
        self.assertEqual(config.pdf_dpi_scale, 3.5)
        self.assertEqual(config.inpaint_radius, 3)
        self.assertTrue(config.use_patch_heal)
        self.assertFalse(config.debug)
        self.assertIn('.pdf', config.supported_extensions)
        self.assertIn('.png', config.supported_extensions)
        self.assertIn('.pptx', config.supported_extensions)

    def test_custom_config(self):
        config = WatermarkConfig(
            search_margin_x=300,
            search_margin_y=80,
            use_patch_heal=False,
            debug=True
        )
        self.assertEqual(config.search_margin_x, 300)
        self.assertEqual(config.search_margin_y, 80)
        self.assertFalse(config.use_patch_heal)
        self.assertTrue(config.debug)


if __name__ == "__main__":
    unittest.main()
