"""Tests for template generation and font resolution."""

import unittest
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from core.template import TemplateRenderer


class TestTemplate(unittest.TestCase):

    def test_template_rendering(self):
        renderer = TemplateRenderer()
        tpl = renderer.render_template(24)
        self.assertIsInstance(tpl, np.ndarray)
        self.assertEqual(tpl.dtype, np.uint8)
        self.assertEqual(tpl.ndim, 2)
        self.assertGreater(tpl.shape[0], 0)
        self.assertGreater(tpl.shape[1], 0)
        # Check caching
        tpl2 = renderer.render_template(24)
        self.assertIs(tpl, tpl2)


if __name__ == "__main__":
    unittest.main()
