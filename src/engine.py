"""Main orchestrator engine dispatching files to format-specific processors."""

import os
import logging
from typing import Optional, List, Dict
from config import WatermarkConfig
from core.detector import WatermarkDetector
from core.reconstructor import PatchReconstructor
from processors.base import BaseProcessor
from processors.pdf import PDFProcessor
from processors.image import ImageProcessor
from processors.pptx import PPTXProcessor
from exceptions import UnsupportedFormatError

logger = logging.getLogger(__name__)


class WatermarkRemover:
    """Unified engine for watermark removal across PDF, PPTX, and image formats."""

    def __init__(
        self,
        config: Optional[WatermarkConfig] = None,
        processors: Optional[List[BaseProcessor]] = None,
    ):
        self.config = config or WatermarkConfig()
        self.detector = WatermarkDetector(self.config)
        self.reconstructor = PatchReconstructor(self.config, self.detector)

        # Register processors
        if processors is not None:
            self.processors = processors
        else:
            self.processors = [
                PDFProcessor(self.config, self.reconstructor),
                ImageProcessor(self.config, self.reconstructor),
                PPTXProcessor(self.config, self.reconstructor),
            ]

    def get_processor(self, file_path: str) -> Optional[BaseProcessor]:
        """Finds the matching processor for a given file path."""
        for processor in self.processors:
            if processor.can_handle(file_path):
                return processor
        return None

    def is_supported(self, file_path: str) -> bool:
        """Returns True if the file extension is supported."""
        return self.get_processor(file_path) is not None

    def default_output_path(self, input_path: str) -> str:
        """Generates the default cleaned output filename for an input path."""
        base, ext = os.path.splitext(input_path)
        return f"{base}_cleaned{ext}"

    def process(self, input_path: str, output_path: Optional[str] = None, **kwargs) -> bool:
        """
        Processes a single file and removes the watermark.
        
        Args:
            input_path: Path to input document or image.
            output_path: Optional destination path (defaults to <name>_cleaned.<ext>).
            **kwargs: Extra parameters passed to the format processor (e.g. preview=True).
            
        Returns:
            True if processed and saved successfully.
        """
        processor = self.get_processor(input_path)
        if processor is None:
            raise UnsupportedFormatError(f"Unsupported file format for: {input_path}")

        if output_path is None:
            output_path = self.default_output_path(input_path)

        return processor.process(input_path, output_path, **kwargs)

    def process_batch(
        self,
        paths: List[str],
        output_dir: Optional[str] = None,
        preview: bool = False
    ) -> Dict[str, bool]:
        """
        Processes a collection of files.
        
        Args:
            paths: List of input file paths.
            output_dir: Optional target directory for all outputs.
            preview: PDF preview flag.
            
        Returns:
            Dictionary mapping each file path to a boolean success status.
        """
        results: Dict[str, bool] = {}
        for path in paths:
            if not self.is_supported(path):
                logger.warning(f"Skipping unsupported file: {path}")
                results[path] = False
                continue

            if output_dir is not None:
                os.makedirs(output_dir, exist_ok=True)
                filename = os.path.basename(path)
                base, ext = os.path.splitext(filename)
                out_path = os.path.join(output_dir, f"{base}_cleaned{ext}")
            else:
                out_path = self.default_output_path(path)

            success = self.process(path, out_path, preview=preview)
            results[path] = success

        return results
