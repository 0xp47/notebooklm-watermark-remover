import os
import sys
import time
import argparse
import logging
from typing import List, Optional

from config import WatermarkConfig
from engine import WatermarkRemover
from ui import TerminalUI
from __init__ import __version__

logger = logging.getLogger("notebooklm_remover")


def get_format_display_name(path: str) -> str:
    """Returns a friendly format name for display."""
    ext = os.path.splitext(path)[1].lower()
    if ext == '.pdf':
        return "PDF Document (.pdf)"
    elif ext == '.pptx':
        return "PowerPoint Presentation (.pptx)"
    elif ext in ('.png', '.jpg', '.jpeg', '.webp'):
        return f"Image File ({ext})"
    return "Unknown Document"


def build_parser() -> argparse.ArgumentParser:
    """Builds and returns the argparse parser with all flags and documentation."""
    parser = argparse.ArgumentParser(
        prog="notebooklm-remover",
        description="Professional watermark remover for PDF, Images, and PPTX documents."
    )
    parser.add_argument(
        "path",
        help="Path to a single file (PDF/PPTX/PNG/JPG/WEBP) or a directory to batch-clean"
    )
    parser.add_argument(
        "-o", "--output",
        help="Custom output file or directory path"
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Process only the first page (PDF only)"
    )
    parser.add_argument(
        "--margin-x",
        type=int,
        default=None,
        help="Search margin width from right edge (pixels/points)"
    )
    parser.add_argument(
        "--margin-y",
        type=int,
        default=None,
        help="Search margin height from bottom edge (pixels/points)"
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=None,
        help="Dark contrast threshold (0-255)"
    )
    parser.add_argument(
        "--text-threshold",
        type=float,
        default=None,
        help="Template match threshold, e.g. 0.45"
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=None,
        help="High-res render/upscale factor (default: 3.5)"
    )
    parser.add_argument(
        "--radius",
        type=int,
        default=None,
        help="Inpaint radius fallback (default: 3)"
    )
    parser.add_argument(
        "--no-patch-heal",
        action="store_true",
        help="Disable clean-patch healing and use plain inpainting instead"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Save intermediate debug masks and images to debug_watermark/"
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )
    return parser


def parse_config(args: argparse.Namespace) -> WatermarkConfig:
    """Instantiates and configures a WatermarkConfig from parsed CLI arguments."""
    config = WatermarkConfig()

    if args.margin_x is not None:
        config.search_margin_x = args.margin_x
    if args.margin_y is not None:
        config.search_margin_y = args.margin_y
    if args.threshold is not None:
        config.pixel_threshold = args.threshold
    if args.text_threshold is not None:
        config.text_match_threshold = args.text_threshold
    if args.scale is not None:
        config.pdf_dpi_scale = args.scale
    if args.radius is not None:
        config.inpaint_radius = args.radius
    if args.no_patch_heal:
        config.use_patch_heal = False
    if args.debug:
        config.debug = True

    return config


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)
    config = parse_config(args)

    log_level = logging.DEBUG if config.debug else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format='%(levelname)s - %(message)s'
    )

    ui = TerminalUI()
    ui.print_banner(__version__)

    remover = WatermarkRemover(config)

    if os.path.isdir(args.path):
        tasks = sorted([
            os.path.join(args.path, f)
            for f in os.listdir(args.path)
            if remover.is_supported(os.path.join(args.path, f))
        ])
        if not tasks:
            ui.print_error(f"No supported files found in directory: {args.path}")
            return 1

        start_time = time.perf_counter()
        progress = ui.create_progress(description="Batch Processing", unit="files")
        results = {}

        if progress is not None:
            with progress:
                batch_task = progress.add_task("Batch Progress", total=len(tasks), patched=0)
                for task_path in tasks:
                    if args.output is not None:
                        os.makedirs(args.output, exist_ok=True)
                        base, ext = os.path.splitext(os.path.basename(task_path))
                        out_path = os.path.join(args.output, f"{base}_cleaned{ext}")
                    else:
                        out_path = remover.default_output_path(task_path)

                    success = remover.process(task_path, out_path, preview=args.preview)
                    results[task_path] = success
                    progress.update(batch_task, advance=1, patched=sum(1 for v in results.values() if v))
        else:
            results = remover.process_batch(tasks, output_dir=args.output, preview=args.preview)

        elapsed = time.perf_counter() - start_time
        ui.print_batch_summary(results, elapsed)
        success_count = sum(1 for status in results.values() if status)
        return 0 if success_count == len(tasks) else 1

    elif os.path.isfile(args.path):
        if not remover.is_supported(args.path):
            ui.print_error(f"Unsupported file format for: {args.path}")
            return 1

        out_path = args.output if args.output else remover.default_output_path(args.path)
        format_name = get_format_display_name(args.path)
        ui.print_file_info(args.path, out_path, format_name, config.use_patch_heal)

        start_time = time.perf_counter()
        unit_name = "slides" if args.path.lower().endswith(".pptx") else ("pages" if args.path.lower().endswith(".pdf") else "image")
        progress = ui.create_progress(description=f"Processing {os.path.basename(args.path)}", unit=unit_name)

        if progress is not None:
            with progress:
                success = remover.process(args.path, out_path, preview=args.preview, progress=progress)
        else:
            success = remover.process(args.path, out_path, preview=args.preview)

        elapsed = time.perf_counter() - start_time

        if success:
            proc = remover.get_processor(args.path)
            stats = getattr(proc, 'last_stats', {'patched': 1, 'total': 1, 'unit': unit_name})
            ui.print_completion(out_path, stats['patched'], stats['total'], elapsed, stats['unit'])
            return 0
        else:
            ui.print_error(f"Failed to clean watermark from: {args.path}")
            return 1

    else:
        ui.print_error(f"Path does not exist: {args.path}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

