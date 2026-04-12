"""Phase 5 — FastAPI HTTP bridge for the Web Chat UI.

Thin transport layer: validates request shape, forwards to the Phase 1
``post_message`` orchestrator contract, and returns the response.  No booking,
MCP, or domain logic lives here.

Entry point (from repo root)::

    uvicorn src.api.http.chat_app:app --reload --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from phase1.api.chat.routes import post_message


def create_app() -> FastAPI:
    # Phase 5 manual QA defaults to deterministic direct MCP execution.
    # Set BOOKING_MCP_DRIVER=llm explicitly if you want Gemini AFC in this surface.
    os.environ.setdefault("BOOKING_MCP_DRIVER", "direct")

    application = FastAPI(title="Advisor Chat API", version="0.1.0")

    origins = os.environ.get(
        "CHAT_API_CORS_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173",
    ).split(",")
    origins = [o.strip() for o in origins if o.strip()]

    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.post("/api/chat/message")
    def chat_message(body: ChatMessageBody) -> dict:
        return post_message(body.session_id, body.text)

    return application


class ChatMessageBody(BaseModel):
    session_id: str = Field(default="web-demo", min_length=1, max_length=128)
    text: str = Field(default="", max_length=16_000)
