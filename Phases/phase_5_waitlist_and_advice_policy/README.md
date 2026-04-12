# Phase 5 — Web Chat UI + HTTP Chat API

Browser-based manual QA surface for the Phase 1–4 chat runtime.

## Components

| Component | Location | Purpose |
|-----------|----------|---------|
| FastAPI bridge | `src/phase5/http/chat_app.py` | Thin HTTP wrapper around `post_message` |
| Uvicorn entry | `src/api/http/chat_app.py` (root) | `sys.path` bootstrap + `create_app()` |
| Vite chat UI | `web/chat-ui/` | Browser client (message thread, input, fetch) |

## Run locally

```bash
# Terminal 1 — Python API (from repo root)
uvicorn src.api.http.chat_app:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 — Vite UI (from web/chat-ui/)
cd web/chat-ui && npm install && npm run dev
```

Open http://localhost:5173 — Vite proxies `/api` requests to port 8000.

## Phase 5 checklist

- [x] `POST /api/chat/message` forwards to `post_message` (Phase 1 orchestrator)
- [x] `GET /api/health` readiness endpoint
- [x] CORS allows local Vite dev origin (`:5173`)
- [x] Web UI: message thread, text input, session badge
- [x] No secrets in the browser; only `session_id` and `text` sent
- [x] Voice placeholder reserved for Phase 6
- [x] HTTP smoke tests via TestClient
- [x] Existing pytest suites remain green
