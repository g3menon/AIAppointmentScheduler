"""FastAPI bridge for Phase 5 Web UI. Calls existing `post_message` (orchestrator).

Run from repo root::

    uvicorn src.api.http.chat_app:app --reload --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_PHASE1_SRC = _ROOT / "Phases" / "phase_1_chat_runtime" / "src"
for _p in (_ROOT, _PHASE1_SRC):
    s = str(_p)
    if s not in sys.path:
        sys.path.insert(0, s)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from phase1.api.chat.routes import post_message

app = FastAPI(title="Advisor Chat API", version="0.1.0")

_origins = os.environ.get("CHAT_API_CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173").split(",")
_origins = [o.strip() for o in _origins if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessageBody(BaseModel):
    session_id: str = Field(default="web-demo", min_length=1, max_length=128)
    text: str = Field(default="", max_length=16_000)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat/message")
def chat_message(body: ChatMessageBody) -> dict:
    return post_message(body.session_id, body.text)
