"""Root conftest — ensure the *local* super_browser package is preferred."""

import sys
from pathlib import Path

# Ensure src/super_browser from THIS repo is always found first,
# even if another editable install shadows it on sys.path.
_src = str(Path(__file__).resolve().parent / "src")
if _src in sys.path:
    sys.path.remove(_src)
sys.path.insert(0, _src)
