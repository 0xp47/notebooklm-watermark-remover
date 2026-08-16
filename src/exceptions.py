"""Custom exception hierarchy for the NotebookLM Watermark Remover."""


class WatermarkRemoverError(Exception):
    """Base exception for all watermark remover errors."""
    pass


class UnsupportedFormatError(WatermarkRemoverError):
    """Raised when an input file has an unsupported file format or extension."""
    pass
