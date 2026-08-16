"""PowerPoint (PPTX) format processor for removing watermarks from slide media."""

import os
import zipfile
import shutil
import tempfile
import logging
from typing import Optional, Tuple
import cv2
import numpy as np

from processors.base import BaseProcessor

logger = logging.getLogger(__name__)


class PPTXProcessor(BaseProcessor):
    """Processes PPTX presentation archives by scanning and cleaning extracted media images."""

    IMAGE_EXTENSIONS: Tuple[str, ...] = ('.png', '.jpg', '.jpeg', '.webp')

    @property
    def supported_extensions(self) -> Tuple[str, ...]:
        return ('.pptx',)

    def clean_pptx_image_bytes(self, img_bytes: bytes, original_ext: str = ".png") -> Optional[bytes]:
        """Decodes, removes watermark from image bytes, and re-encodes preserving format/alpha."""
        arr = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
        if img is None:
            return None

        h, w = img.shape[:2]
        has_alpha = len(img.shape) == 3 and img.shape[2] == 4

        if has_alpha:
            channels = cv2.split(img)
            img_bgr = cv2.merge(channels[:3])
            alpha = channels[3]
        else:
            img_bgr = img.copy()
            alpha = None

        mx, my = self.config.search_margin_x, self.config.search_margin_y
        y0, x0 = max(0, h - my), max(0, w - mx)

        roi = img_bgr[y0:h, x0:w].copy()

        # Upscale ROI for sub-pixel accuracy
        scale = self.config.pdf_dpi_scale
        roi_hr = cv2.resize(roi, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
        result = self.reconstructor.clean_roi(roi_hr)
        if result is None:
            return None

        cleaned_hr, mask_hr = result
        cleaned = cv2.resize(cleaned_hr, (w - x0, h - y0), interpolation=cv2.INTER_LINEAR)
        mask = cv2.resize(mask_hr, (w - x0, h - y0), interpolation=cv2.INTER_NEAREST)

        roi[mask > 0] = cleaned[mask > 0]
        img_bgr[y0:h, x0:w] = roi

        img_final = cv2.merge([*cv2.split(img_bgr), alpha]) if has_alpha else img_bgr

        ext = original_ext.lower()
        if ext in ('.jpg', '.jpeg') and not has_alpha:
            ok, encoded = cv2.imencode('.jpg', img_final, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        elif ext == '.webp':
            ok, encoded = cv2.imencode('.webp', img_final, [int(cv2.IMWRITE_WEBP_QUALITY), 95])
        else:
            ok, encoded = cv2.imencode('.png', img_final)

        return encoded.tobytes() if ok else None

    def process(self, input_path: str, output_path: str, **kwargs) -> bool:
        """Extracts PPTX media images, cleans watermark artifacts, and repacks archive."""
        tmpdir = None
        ui_progress = kwargs.get('progress')
        task_id = kwargs.get('task_id')
        try:
            tmpdir = tempfile.mkdtemp()
            with zipfile.ZipFile(input_path, 'r') as zin:
                zin.extractall(tmpdir)

            media_dir = os.path.join(tmpdir, 'ppt', 'media')
            if not os.path.isdir(media_dir):
                logger.error(f"No media directory found inside PPTX: {input_path}")
                shutil.rmtree(tmpdir)
                return False

            images = sorted([f for f in os.listdir(media_dir) if f.lower().endswith(self.IMAGE_EXTENSIONS)])
            if not images:
                logger.error(f"No images found inside PPTX: {input_path}")
                shutil.rmtree(tmpdir)
                return False

            patched = 0
            created_task = False
            if ui_progress is not None and task_id is None:
                task_id = ui_progress.add_task(
                    f"Processing {os.path.basename(input_path)}",
                    total=len(images),
                    unit="slides",
                    patched=0,
                )
                created_task = True

            for img_name in images:
                img_path = os.path.join(media_dir, img_name)
                with open(img_path, 'rb') as f:
                    original = f.read()

                ext = os.path.splitext(img_name)[1]
                cleaned = self.clean_pptx_image_bytes(original, ext)
                if cleaned is not None:
                    with open(img_path, 'wb') as f:
                        f.write(cleaned)
                    patched += 1

                if ui_progress is not None and task_id is not None:
                    ui_progress.update(task_id, advance=1, patched=patched)

            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zout:
                for root, _, files in os.walk(tmpdir):
                    for fname in files:
                        full_path = os.path.join(root, fname)
                        arcname = os.path.relpath(full_path, tmpdir)
                        zout.write(full_path, arcname)

            shutil.rmtree(tmpdir)
            self.last_stats = {'patched': patched, 'total': len(images), 'unit': 'slide images'}
            logger.info(f"Saved {output_path} ({patched}/{len(images)} images patched)")
            return True

        except Exception as e:
            logger.error(f"Error processing PPTX {input_path}: {e}")
            if tmpdir and os.path.isdir(tmpdir):
                shutil.rmtree(tmpdir)
            return False
