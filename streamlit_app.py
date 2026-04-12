"""Shim: canonical Phase 9 Streamlit app lives in ``Phases/phase_9_streamlit_deploy/``."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "Phases" / "phase_9_streamlit_deploy" / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from phase9.app import main

main()
