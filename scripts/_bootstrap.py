"""Imported first by each script: running `python scripts/x.py` puts only scripts/ on the path."""

from pathlib import Path
import sys

root = str(Path(__file__).resolve().parents[1])
if root not in sys.path:
    sys.path.insert(0, root)
