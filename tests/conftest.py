"""Pytest configuration and environment setup."""

import os
import sys

# Add src/ to sys.path so tests can import notebooklm_remover without explicit installation
SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)
