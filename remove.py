#!/usr/bin/env python3
"""CLI entry point for NotebookLM Watermark Remover."""

import os
import sys

# Ensure src directory is available on sys.path
_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from cli import main

if __name__ == "__main__":
    sys.exit(main())
