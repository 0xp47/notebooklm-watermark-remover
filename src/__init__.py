"""NotebookLM Watermark Remover - A modular tool for cleaning watermarks from PDF, PPTX, and images."""

__version__ = "1.0.0"

from config import WatermarkConfig
from engine import WatermarkRemover
from exceptions import (
    WatermarkRemoverError,
    UnsupportedFormatError,
)
from core.detector import WatermarkDetector
from core.reconstructor import PatchReconstructor
from core.template import TemplateRenderer
from processors.base import BaseProcessor
from processors.pdf import PDFProcessor
from processors.image import ImageProcessor
from processors.pptx import PPTXProcessor

__all__ = [
    "__version__",
    "WatermarkConfig",
    "WatermarkRemover",
    "WatermarkRemoverError",
    "UnsupportedFormatError",
    "WatermarkDetector",
    "PatchReconstructor",
    "TemplateRenderer",
    "BaseProcessor",
    "PDFProcessor",
    "ImageProcessor",
    "PPTXProcessor",
]
