"""Root pytest configuration adding src/ to sys.path."""

import os
import sys

_src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)
