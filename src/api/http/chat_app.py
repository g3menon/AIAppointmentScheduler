"""Uvicorn entry point — bootstraps sys.path then delegates to Phase 5 canonical module.

Run from repo root::

    uvicorn src.api.http.chat_app:app --reload --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_PHASE1_SRC = _ROOT / "Phases" / "phase_1_chat_runtime" / "src"
_PHASE3_SRC = _ROOT / "Phases" / "phase_3_nlu_and_mcp" / "src"
_PHASE4_SRC = _ROOT / "Phases" / "phase_4_reliability_observability" / "src"
_PHASE5_SRC = _ROOT / "Phases" / "phase_5_waitlist_and_advice_policy" / "src"
_PHASE8_SRC = _ROOT / "Phases" / "phase_8_hardening_ops" / "src"

for _p in (_ROOT, _PHASE1_SRC, _PHASE3_SRC, _PHASE4_SRC, _PHASE5_SRC, _PHASE8_SRC):
    s = str(_p)
    if s not in sys.path:
        sys.path.insert(0, s)

from phase5.http.chat_app import create_app  # noqa: E402

app = create_app()
