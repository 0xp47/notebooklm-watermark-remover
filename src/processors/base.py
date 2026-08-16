"""Abstract base processor defining the document/image processor interface."""

from abc import ABC, abstractmethod
from typing import Optional, Tuple
from config import WatermarkConfig
from core.reconstructor import PatchReconstructor


class BaseProcessor(ABC):
    """Abstract base class for all file format processors."""

    def __init__(self, config: Optional[WatermarkConfig] = None, reconstructor: Optional[PatchReconstructor] = None):
        self.config = config or WatermarkConfig()
        self.reconstructor = reconstructor or PatchReconstructor(self.config)

    @property
    @abstractmethod
    def supported_extensions(self) -> Tuple[str, ...]:
        """Tuple of file extensions supported by this processor (e.g. ('.pdf',))."""
        pass

    def can_handle(self, file_path: str) -> bool:
        """Returns True if this processor supports the given file path based on extension."""
        return file_path.lower().endswith(self.supported_extensions)

    @abstractmethod
    def process(self, input_path: str, output_path: str, **kwargs) -> bool:
        """
        Processes the input file, removes the watermark, and saves to output_path.
        
        Args:
            input_path: Path to the source file.
            output_path: Destination path for the cleaned file.
            **kwargs: Format-specific processing options (e.g. preview=True for PDF).
            
        Returns:
            True if processing succeeded, False otherwise.
        """
        pass
