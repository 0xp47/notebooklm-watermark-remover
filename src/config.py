"""Configuration settings and dataclasses for watermark detection and removal."""

from dataclasses import dataclass, field
from typing import Tuple


@dataclass
class WatermarkConfig:
    """Configuration parameters for watermark detection, mask extraction, and reconstruction."""

    # Search margins from the bottom-right corner (in pixels / PDF points)
    search_margin_x: int = 400
    search_margin_y: int = 120

    # Extra padding around detected watermark bounding box
    watermark_padding: int = 6

    # Threshold for contrast-based candidate extraction (0-255)
    pixel_threshold: int = 22

    # PDF rendering / high-resolution scaling factor
    pdf_dpi_scale: float = 3.5

    # Inpainting radius for cv2.inpaint (used as fallback)
    inpaint_radius: int = 3

    # Connected component area filters
    min_watermark_area: int = 400
    min_component_area: int = 18
    max_component_area_ratio: float = 0.25

    # Text & template detection parameters
    text_match_threshold: float = 0.45
    text_luma_threshold: int = 210
    roi_bottom_bias: float = 0.35
    roi_right_bias: float = 0.45

    # Morphological operations
    dilate_iterations: int = 1
    close_iterations: int = 1

    # Reconstruction strategy
    use_patch_heal: bool = True

    # Debug mode (saves intermediate masks and ROIs to debug_watermark/)
    debug: bool = False

    # Supported file extensions
    supported_extensions: Tuple[str, ...] = field(
        default=('.pdf', '.pptx', '.png', '.jpg', '.jpeg', '.webp')
    )
