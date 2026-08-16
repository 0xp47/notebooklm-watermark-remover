"""Processors for handling specific document and image file formats."""

from processors.base import BaseProcessor
from processors.image import ImageProcessor
from processors.pdf import PDFProcessor
from processors.pptx import PPTXProcessor

__all__ = [
    "BaseProcessor",
    "ImageProcessor",
    "PDFProcessor",
    "PPTXProcessor",
]
