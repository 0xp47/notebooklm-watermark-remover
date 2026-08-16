"""Tests for base and format-specific processors."""

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from processors.pdf import PDFProcessor
from processors.image import ImageProcessor
from processors.pptx import PPTXProcessor


class TestProcessors(unittest.TestCase):

    def test_processor_extensions(self):
        pdf_p = PDFProcessor()
        img_p = ImageProcessor()
        pptx_p = PPTXProcessor()

        self.assertTrue(pdf_p.can_handle("document.pdf"))
        self.assertTrue(pdf_p.can_handle("DOC.PDF"))
        self.assertFalse(pdf_p.can_handle("document.docx"))

        self.assertTrue(img_p.can_handle("image.png"))
        self.assertTrue(img_p.can_handle("photo.jpg"))
        self.assertTrue(img_p.can_handle("photo.JPEG"))
        self.assertTrue(img_p.can_handle("graphic.webp"))
        self.assertFalse(img_p.can_handle("image.gif"))

        self.assertTrue(pptx_p.can_handle("presentation.pptx"))
        self.assertFalse(pptx_p.can_handle("presentation.ppt"))

    def test_image_processor_file_not_found(self):
        img_p = ImageProcessor()
        self.assertFalse(img_p.process("non_existent_file.png", "out.png"))

    def test_pdf_processor_file_not_found(self):
        pdf_p = PDFProcessor()
        self.assertFalse(pdf_p.process("non_existent_file.pdf", "out.pdf"))

    def test_pptx_processor_file_not_found(self):
        pptx_p = PPTXProcessor()
        self.assertFalse(pptx_p.process("non_existent_file.pptx", "out.pptx"))


if __name__ == "__main__":
    unittest.main()
