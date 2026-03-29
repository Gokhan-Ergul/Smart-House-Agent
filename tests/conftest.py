import sys
from pathlib import Path

# src layout: tests run with pythonpath = src via pyproject.toml
_ROOT = Path(__file__).resolve().parents[1]
_src = _ROOT / "src"
if _src.exists() and str(_src) not in sys.path:
    sys.path.insert(0, str(_src))
