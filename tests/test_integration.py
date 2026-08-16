"""Integration tests for end-to-end PDF, PPTX, Image, and batch processing."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
import pymupdf as fitz
try:
    import pptx
    from pptx.util import Inches
except ImportError:
    pptx = None

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from engine import WatermarkRemover
from cli import main
from processors.pdf import PDFProcessor
from processors.image import ImageProcessor
from processors.pptx import PPTXProcessor


class TestIntegration(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        if os.path.exists(self.tmpdir):
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_image_end_to_end(self):
        # Create a synthetic image with a bottom-right watermark
        img_path = os.path.join(self.tmpdir, "sample.png")
        out_path = os.path.join(self.tmpdir, "sample_cleaned.png")

        canvas = np.full((300, 600, 3), 245, dtype=np.uint8)
        # Add NotebookLM text in the bottom right corner
        cv2.putText(canvas, "NotebookLM", (420, 275), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (40, 40, 40), 2)
        cv2.imwrite(img_path, canvas)

        processor = ImageProcessor()
        success = processor.process(img_path, out_path)
        self.assertTrue(success)
        self.assertTrue(os.path.isfile(out_path))

    def test_image_with_alpha_end_to_end(self):
        # Create a synthetic 4-channel RGBA PNG image
        img_path = os.path.join(self.tmpdir, "sample_alpha.png")
        out_path = os.path.join(self.tmpdir, "sample_alpha_cleaned.png")

        canvas = np.full((300, 600, 4), 255, dtype=np.uint8)
        canvas[:, :, 3] = 255
        cv2.putText(canvas, "NotebookLM", (420, 275), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (40, 40, 40, 255), 2)
        cv2.imwrite(img_path, canvas)

        processor = ImageProcessor()
        success = processor.process(img_path, out_path)
        self.assertTrue(success)
        self.assertTrue(os.path.isfile(out_path))

    def test_pdf_end_to_end(self):
        # Create a synthetic 2-page PDF
        pdf_path = os.path.join(self.tmpdir, "sample.pdf")
        out_path = os.path.join(self.tmpdir, "sample_cleaned.pdf")

        doc = fitz.open()
        page1 = doc.new_page(width=612, height=792)
        page1.insert_text(fitz.Point(450, 760), "NotebookLM", fontsize=12)
        page2 = doc.new_page(width=612, height=792)
        page2.insert_text(fitz.Point(450, 760), "NotebookLM", fontsize=12)
        doc.save(pdf_path)
        doc.close()

        processor = PDFProcessor()
        success = processor.process(pdf_path, out_path, preview=False)
        self.assertTrue(success)
        self.assertTrue(os.path.isfile(out_path))

    def test_pdf_preview_mode(self):
        # Test preview flag processing only first page
        pdf_path = os.path.join(self.tmpdir, "preview.pdf")
        out_path = os.path.join(self.tmpdir, "preview_cleaned.pdf")

        doc = fitz.open()
        page1 = doc.new_page(width=612, height=792)
        page1.insert_text(fitz.Point(450, 760), "NotebookLM", fontsize=12)
        page2 = doc.new_page(width=612, height=792)
        page2.insert_text(fitz.Point(450, 760), "NotebookLM", fontsize=12)
        doc.save(pdf_path)
        doc.close()

        processor = PDFProcessor()
        success = processor.process(pdf_path, out_path, preview=True)
        self.assertTrue(success)
        self.assertTrue(os.path.isfile(out_path))

    def test_pptx_end_to_end(self):
        import zipfile
        pptx_path = os.path.join(self.tmpdir, "sample.pptx")
        out_path = os.path.join(self.tmpdir, "sample_cleaned.pptx")

        # Create image to embed inside PPTX archive
        bg_canvas = np.full((400, 800, 3), 240, dtype=np.uint8)
        cv2.putText(bg_canvas, "NotebookLM", (600, 370), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 50), 2)
        _, img_bytes = cv2.imencode('.png', bg_canvas)

        # Create a valid minimal PPTX structure (zip container with ppt/media)
        with zipfile.ZipFile(pptx_path, 'w') as z:
            z.writestr('[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
            z.writestr('ppt/media/image1.png', img_bytes.tobytes())

        processor = PPTXProcessor()
        success = processor.process(pptx_path, out_path)
        self.assertTrue(success)
        self.assertTrue(os.path.isfile(out_path))

    def test_batch_processing_and_cli(self):
        # Create multiple files in a folder and test batch processing via CLI
        folder = os.path.join(self.tmpdir, "batch_folder")
        os.makedirs(folder, exist_ok=True)

        img1 = np.full((200, 400, 3), 250, dtype=np.uint8)
        cv2.putText(img1, "NotebookLM", (260, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30), 2)
        cv2.imwrite(os.path.join(folder, "doc1.png"), img1)

        # Run engine batch
        remover = WatermarkRemover()
        res = remover.process_batch([os.path.join(folder, "doc1.png")])
        self.assertTrue(res[os.path.join(folder, "doc1.png")])

        # Run CLI on directory
        exit_code = main([folder])
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
