"""Tests for the WatermarkRemover engine and processor orchestration."""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from engine import WatermarkRemover
from exceptions import UnsupportedFormatError
from processors.pdf import PDFProcessor
from processors.image import ImageProcessor
from processors.pptx import PPTXProcessor


class TestEngine(unittest.TestCase):

    def test_engine_init(self):
        remover = WatermarkRemover()
        self.assertEqual(len(remover.processors), 3)
        self.assertTrue(remover.is_supported("test.pdf"))
        self.assertTrue(remover.is_supported("test.png"))
        self.assertTrue(remover.is_supported("test.pptx"))
        self.assertFalse(remover.is_supported("test.txt"))

    def test_engine_get_processor(self):
        remover = WatermarkRemover()
        self.assertIsInstance(remover.get_processor("file.pdf"), PDFProcessor)
        self.assertIsInstance(remover.get_processor("file.jpg"), ImageProcessor)
        self.assertIsInstance(remover.get_processor("file.pptx"), PPTXProcessor)
        self.assertIsNone(remover.get_processor("file.unknown"))

    def test_engine_unsupported_format(self):
        remover = WatermarkRemover()
        with self.assertRaises(UnsupportedFormatError):
            remover.process("file.unsupported")

    def test_engine_default_output_path(self):
        remover = WatermarkRemover()
        self.assertEqual(remover.default_output_path("doc.pdf"), "doc_cleaned.pdf")
        self.assertEqual(remover.default_output_path("path/to/slide.png"), "path/to/slide_cleaned.png")


if __name__ == "__main__":
    unittest.main()
