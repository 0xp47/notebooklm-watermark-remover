"""Tests for CLI arguments parsing and commands."""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cli import build_parser, parse_config, main


class TestCLI(unittest.TestCase):

    def test_build_parser(self):
        parser = build_parser()
        args = parser.parse_args(["input.pdf", "--margin-x", "350", "--no-patch-heal", "--debug"])
        self.assertEqual(args.path, "input.pdf")
        self.assertEqual(args.margin_x, 350)
        self.assertTrue(args.no_patch_heal)
        self.assertTrue(args.debug)

    def test_parse_config(self):
        parser = build_parser()
        args = parser.parse_args([
            "input.pdf",
            "--margin-x", "250",
            "--margin-y", "90",
            "--threshold", "30",
            "--text-threshold", "0.55",
            "--scale", "4.0",
            "--radius", "5",
            "--no-patch-heal",
            "--debug"
        ])
        config = parse_config(args)
        self.assertEqual(config.search_margin_x, 250)
        self.assertEqual(config.search_margin_y, 90)
        self.assertEqual(config.pixel_threshold, 30)
        self.assertEqual(config.text_match_threshold, 0.55)
        self.assertEqual(config.pdf_dpi_scale, 4.0)
        self.assertEqual(config.inpaint_radius, 5)
        self.assertFalse(config.use_patch_heal)
        self.assertTrue(config.debug)

    def test_main_non_existent_file(self):
        code = main(["non_existent_file_path_12345.pdf"])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
