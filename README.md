# NotebookLM Watermark Remover

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License MIT">
  <img src="https://img.shields.io/badge/interface-Pure%20CLI-orange.svg" alt="Pure CLI">
  <img src="https://img.shields.io/badge/tests-19%20passed-brightgreen.svg" alt="Tests Passing">
</p>

A fast, lightweight, and pure Python CLI tool designed to cleanly detect and remove "NotebookLM" watermarks from **PDF documents**, **PowerPoint presentations (PPTX)**, and **images (PNG, JPG, WEBP)**.

Instead of crudely placing solid blocks or blurring areas, it uses a hybrid approach: **PyMuPDF vector layer redaction**, **multi-scale template matching**, and **texture-preserving background patch healing** (with Telea inpainting fallback).

---

## Key Features

- **Pure CLI Experience**: Lightweight Python script execution with zero heavy build tools, GUI overhead, or packaging bloat.
- **Smart PDF Redaction**: Selectively removes the watermark from the PDF vector text layer, keeping background vector art intact while inpainting watermark icons.
- **PowerPoint (PPTX) Support**: Automatically scans, cleans, and updates embedded slide images inside PPTX archives while maintaining layout and image compression.
- **Image Cleaning**: Restores PNGs (including alpha/transparency channels), JPEGs, and WEBPs with sub-pixel resolution upscaling.
- **Texture-Preserving Patch Healing**: Samples neighboring clean background regions to preserve grain, gradients, and paper textures.
- **Batch Processing**: Clean entire folders containing mixed document and image formats in a single command.
- **Preview Mode**: Fast preview on page 1 of PDFs before committing to large multi-page jobs.

---

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/0xp47/notebooklm-watermark-remover.git
cd notebooklm-watermark-remover
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

*(Optional)* Install locally as a system-wide command:
```bash
pip install -e .
```

---

## Quick Start & CLI Usage

Run directly via the root `remove.py` script:

### Single File Cleaning
```bash
# Clean a PDF document
python remove.py document.pdf

# Clean a PowerPoint slide deck
python remove.py presentation.pptx

# Clean an image (PNG with transparency, JPG, WEBP)
python remove.py slide.png
```
*Cleaned files are saved automatically in the same directory with `_cleaned` suffix (e.g., `document_cleaned.pdf`).*

### Custom Output Destination
```bash
python remove.py document.pdf -o path/to/cleaned_output.pdf
```

### Batch Process a Folder
```bash
# Clean all supported files in a folder
python remove.py ./my_documents/

# Clean and output all results to a specific directory
python remove.py ./my_documents/ -o ./cleaned_documents/
```

### Preview First Page (PDF Only)
```bash
python remove.py document.pdf --preview
```

---

## CLI Options & Tuning

```
usage: notebooklm-remover [-h] [-o OUTPUT] [--preview] [--margin-x MARGIN_X]
                          [--margin-y MARGIN_Y] [--threshold THRESHOLD]
                          [--text-threshold TEXT_THRESHOLD] [--scale SCALE]
                          [--radius RADIUS] [--no-patch-heal] [--debug] [-v]
                          path
```

| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `path` | `str` | *Required* | Path to an input file (`.pdf`, `.pptx`, `.png`, `.jpg`, `.jpeg`, `.webp`) or folder. |
| `-o, --output` | `str` | `None` | Custom output file or directory path (defaults to `<name>_cleaned.<ext>`). |
| `--preview` | `flag` | `False` | Process only the first page (PDF only). |
| `--margin-x` | `int` | `400` | Search margin width from right edge (pixels/points). |
| `--margin-y` | `int` | `120` | Search margin height from bottom edge (pixels/points). |
| `--threshold` | `int` | `22` | Contrast difference threshold for candidate stroke extraction (0–255). |
| `--text-threshold` | `float` | `0.45` | Template match correlation threshold for "NotebookLM" text detection. |
| `--scale` | `float` | `3.5` | Upscaling render factor for high-resolution sub-pixel mask alignment. |
| `--radius` | `int` | `3` | Inpaint radius for OpenCV Telea fallback. |
| `--no-patch-heal` | `flag` | `False` | Disable texture patch healing and use standard inpainting directly. |
| `--debug` | `flag` | `False` | Output intermediate detection masks and ROIs to `debug_watermark/`. |
| `-v, --version` | `flag` | — | Display version number (`1.0.0`) and exit. |

---

## How It Works

```
                        ┌───────────────────────────────┐
                        │          Input File           │
                        └──────────────┬────────────────┘
                                       │
                ┌──────────────────────┼──────────────────────┐
                ▼                      ▼                      ▼
           [ PDF Document ]      [ PPTX Archive ]       [ Image File ]
                │                      │                      │
        Vector Redaction        Unpack Media            Upscale ROI
                │                      │                      │
                └──────────────┬───────┴──────────────────────┘
                               ▼
               ┌───────────────────────────────┐
               │    Watermark Detection ROI    │
               │   • Polarity check (L/D)      │
               │   • Multi-scale template      │
               │   • Connected component fusion│
               └───────────────┬───────────────┘
                               ▼
               ┌───────────────────────────────┐
               │      Reconstruction Core      │
               │   • Texture donor patch match │
               │   • Alpha gradient blending   │
               │   • Telea inpaint fallback    │
               └───────────────┬───────────────┘
                               ▼
               ┌───────────────────────────────┐
               │     Cleaned Output Saved      │
               └───────────────────────────────┘
```

---

## Project Structure

```
notebooklm-watermark-remover/
├── src/
│   ├── __init__.py          # Package exports
│   ├── __main__.py          # Module execution wrapper
│   ├── cli.py               # Pure CLI argument parsing & orchestration
│   ├── config.py            # WatermarkConfig dataclass
│   ├── engine.py            # Unified WatermarkRemover engine
│   ├── exceptions.py        # Custom exception types
│   ├── ui.py                # Rich terminal UI, live progress & summaries
│   ├── core/
│   │   ├── detector.py      # Multi-scale template matching & mask builder
│   │   ├── reconstructor.py # Donor patch healing & inpainting
│   │   └── template.py      # Cross-platform font resolution & template caching
│   └── processors/
│       ├── base.py          # Abstract processor base class
│       ├── image.py         # Image format processor (PNG, JPG, WEBP)
│       ├── pdf.py           # PDF PyMuPDF vector & raster processor
│       └── pptx.py          # PPTX presentation media processor
├── tests/                   # Complete unit & integration test suite (25 test cases)
├── remove.py                # Direct root CLI entrypoint script
├── requirements.txt         # Pure CLI dependencies
├── pyproject.toml           # Packaging configuration
├── pytest.ini               # Test configuration
└── .gitignore               # Clean Git ignore rules
```

---

## Running the Test Suite

```bash
# Run with pytest
python -m pytest -v

# Or run with unittest
python -m unittest discover -s tests -v
```

---

## License & Disclaimer

- **License**: Released under the [MIT License](LICENSE).
- **Disclaimer**: This tool is intended for personal and fair-use document cleaning on presentations and materials you own or have permission to modify.
