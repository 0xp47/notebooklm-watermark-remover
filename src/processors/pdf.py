"""PDF format processor using PyMuPDF for vector redaction and raster patching."""

import os
import io
import logging
from typing import Optional, Tuple
import cv2
import numpy as np
from PIL import Image
import pymupdf as fitz

from processors.base import BaseProcessor

logger = logging.getLogger(__name__)


class PDFProcessor(BaseProcessor):
    """Processes PDF documents, performing selective vector redaction and raster inpainting."""

    WATERMARK_TEXT: str = "NotebookLM"

    @property
    def supported_extensions(self) -> Tuple[str, ...]:
        return ('.pdf',)

    def _pixmap_to_bgr(self, pix: fitz.Pixmap) -> Optional[np.ndarray]:
        """Converts a PyMuPDF Pixmap to an OpenCV BGR numpy array."""
        data = np.frombuffer(pix.samples, dtype=np.uint8)
        if pix.n == 4:
            return cv2.cvtColor(data.reshape(pix.h, pix.w, 4), cv2.COLOR_RGBA2BGR)
        if pix.n == 3:
            return cv2.cvtColor(data.reshape(pix.h, pix.w, 3), cv2.COLOR_RGB2BGR)
        if pix.n == 1:
            gray = data.reshape(pix.h, pix.w)
            return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        return None

    def find_watermark_text_rect(self, page: fitz.Page) -> Optional[fitz.Rect]:
        """
        Locates the watermark text via the PDF text layer.
        Returns a padded Rect suitable for redaction, or None if not found in text layer.
        """
        w, h = page.rect.width, page.rect.height
        instances = page.search_for(self.WATERMARK_TEXT)
        if not instances:
            return None

        best = None
        best_score = float('inf')
        for rect in instances:
            cy = (rect.y0 + rect.y1) / 2.0
            cx = (rect.x0 + rect.x1) / 2.0
            if cy < h * 0.78:
                continue
            if cx < w * 0.70:
                continue
            if rect.width > 260 or rect.height > 50:
                continue
            dist = abs(w - cx) + abs(h - cy)
            if dist < best_score:
                best_score = dist
                best = rect

        if best is None:
            return None

        pad = self.config.watermark_padding
        return fitz.Rect(
            max(0, best.x0 - pad),
            max(0, best.y0 - pad),
            min(w, best.x1 + pad),
            min(h, best.y1 + pad),
        )

    def find_watermark_icon_zone(self, text_rect: fitz.Rect, page_w: float, page_h: float) -> fitz.Rect:
        """Region to the left of the watermark text where the NotebookLM icon glyph sits."""
        return fitz.Rect(
            max(0, text_rect.x0 - 95),
            max(0, text_rect.y0 - 18),
            min(page_w, text_rect.x0 + 8),
            min(page_h, text_rect.y1 + 18),
        )

    def redact_pdf_text(self, page: fitz.Page, rect: fitz.Rect) -> bool:
        """
        Removes the watermark text from the vector text layer via redaction annotations.
        Leaves the underlying vector backgrounds untouched.
        """
        try:
            page.add_redact_annot(rect, fill=None)
            try:
                page.apply_redactions(
                    images=fitz.PDF_REDACT_IMAGE_NONE,
                    graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                    text=fitz.PDF_REDACT_TEXT_REMOVE,
                )
            except TypeError:
                page.apply_redactions()
        except Exception as e:
            logger.debug(f"Redaction failed on page {page.number}: {e}")
            return False

        return not page.search_for(self.WATERMARK_TEXT)

    def patch_pdf_rect(self, page: fitz.Page, rect: fitz.Rect) -> bool:
        """
        Renders a given rect, detects and reconstructs the watermark inside it,
        and reinserts only the tight bounding box around the detected mask.
        """
        mat = fitz.Matrix(self.config.pdf_dpi_scale, self.config.pdf_dpi_scale)
        pix = page.get_pixmap(clip=rect, matrix=mat, alpha=False)
        roi_bgr = self._pixmap_to_bgr(pix)
        if roi_bgr is None:
            return False

        result = self.reconstructor.clean_roi(roi_bgr)
        if result is None:
            return False
        cleaned, mask = result

        x, y, bw, bh = cv2.boundingRect(mask)
        px = max(2, self.config.watermark_padding)
        x0 = max(0, x - px)
        y0 = max(0, y - px)
        x1 = min(roi_bgr.shape[1], x + bw + px)
        y1 = min(roi_bgr.shape[0], y + bh + px)

        scale = self.config.pdf_dpi_scale
        sub_rect = fitz.Rect(
            rect.x0 + x0 / scale, rect.y0 + y0 / scale,
            rect.x0 + x1 / scale, rect.y0 + y1 / scale,
        )

        sub_rgb = cv2.cvtColor(cleaned[y0:y1, x0:x1], cv2.COLOR_BGR2RGB)
        buf = io.BytesIO()
        Image.fromarray(sub_rgb).save(buf, format='PNG')
        page.insert_image(sub_rect, stream=buf.getvalue(), overlay=True)
        return True

    def process(self, input_path: str, output_path: str, preview: bool = False, **kwargs) -> bool:
        """
        Processes all pages in a PDF document to remove watermarks.
        
        Args:
            input_path: Path to the input PDF file.
            output_path: Path to save the cleaned PDF.
            preview: If True, processes only the first page.
        """
        ui_progress = kwargs.get('progress')
        task_id = kwargs.get('task_id')
        try:
            doc = fitz.open(input_path)
        except Exception as e:
            logger.error(f"Could not open PDF {input_path}: {e}")
            return False

        filename = os.path.basename(input_path)
        total_pages = len(doc)
        limit_pages = 1 if preview else total_pages

        patched = skipped = 0
        if ui_progress is not None and task_id is None:
            task_id = ui_progress.add_task(
                f"Processing {filename}",
                total=limit_pages,
                unit="pages",
                patched=0,
            )

        for i, page in enumerate(doc):
            if preview and i > 0:
                break

            w, h = page.rect.width, page.rect.height
            patched_now = False

            text_rect = self.find_watermark_text_rect(page)
            if text_rect is not None:
                icon_zone = self.find_watermark_icon_zone(text_rect, w, h)
                if self.redact_pdf_text(page, text_rect):
                    # Clean any non-text icon residue
                    self.patch_pdf_rect(page, icon_zone)
                    patched_now = True
                else:
                    patched_now = self.patch_pdf_rect(page, text_rect | icon_zone)

            if not patched_now:
                # Scanned/rasterized PDF fallback: scan corner visually
                corner = fitz.Rect(
                    max(0, w - self.config.search_margin_x),
                    max(0, h - self.config.search_margin_y),
                    w,
                    h,
                )
                patched_now = self.patch_pdf_rect(page, corner)

            if patched_now:
                patched += 1
            else:
                skipped += 1

            if ui_progress is not None and task_id is not None:
                ui_progress.update(task_id, advance=1, patched=patched)

        try:
            doc.save(output_path, garbage=3, deflate=True, clean=True)
            doc.close()
            self.last_stats = {'patched': patched, 'total': limit_pages, 'unit': 'pages'}
            logger.info(f"Saved {output_path} ({patched} pages patched, {skipped} skipped)")
            return True
        except Exception as e:
            logger.error(f"Error saving PDF to {output_path}: {e}")
            return False
