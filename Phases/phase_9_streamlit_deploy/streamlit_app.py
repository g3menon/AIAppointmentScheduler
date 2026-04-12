"""Phase 9 Streamlit entry — presentation only; backend API holds domain/MCP logic.

Run from repository root::

    streamlit run Phases/phase_9_streamlit_deploy/streamlit_app.py

Or use the root shim::

    streamlit run streamlit_app.py

Environment:

- ``CHAT_API_BASE_URL`` — chat API base (default ``http://127.0.0.1:8000``).
  On Streamlit Community Cloud, set the same key in app secrets.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from phase9.app import main

main()
