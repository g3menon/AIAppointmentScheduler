# Phase 9 — Streamlit deployment (presentation only)

Canonical app code lives here. The UI talks to the FastAPI chat API only; it does not call MCP or Google APIs directly.

## Layout

- `streamlit_app.py` — Streamlit entry (adjusts `sys.path`, calls `phase9.app.main()`).
- `src/phase9/chat_client.py` — HTTP client for `/api/chat/message` and `/api/health`.
- `src/phase9/app.py` — Streamlit layout: session state, quick replies, intent preview, booking summary card.
- `.streamlit/config.toml` — server/theme defaults for local runs from this directory.
- `.streamlit/secrets.toml.example` — template for `CHAT_API_BASE_URL` on Streamlit Cloud (do not commit real secrets).

Repository root `streamlit_app.py` is a thin shim that imports the same `phase9.app.main()`.

## Tests

```bash
pytest Phases/phase_9_streamlit_deploy/tests/ -v
```

## Local run

1. Start the API (from repo root):

   ```bash
   uvicorn src.api.http.chat_app:app --host 127.0.0.1 --port 8000
   ```

2. Start Streamlit (from repo root):

   ```bash
   streamlit run Phases/phase_9_streamlit_deploy/streamlit_app.py
   ```

   Or:

   ```bash
   streamlit run streamlit_app.py
   ```

3. Optional: point to a non-default API:

   ```bash
   set CHAT_API_BASE_URL=http://127.0.0.1:8000
   streamlit run streamlit_app.py
   ```

## Streamlit Community Cloud

1. Create a **separate** deployment for the **FastAPI** backend (Render, Fly.io, Cloud Run, etc.) and expose `https://your-api...` with `/api/chat/message` and `/api/health`.

2. Connect the GitHub repo to Streamlit Cloud; set **Main file path** to `Phases/phase_9_streamlit_deploy/streamlit_app.py` (or `streamlit_app.py` if you prefer the root shim — both work if `sys.path` includes `Phases/phase_9_streamlit_deploy/src`).

3. In **Secrets**, add:

   ```toml
   CHAT_API_BASE_URL = "https://your-api.example.com"
   ```

   The app copies this into the process environment on startup.

4. **Python dependencies**: ensure `requirements.txt` at repo root includes `streamlit` (already listed).

5. **CORS**: set `CHAT_API_CORS_ORIGINS` on the API host to include your Streamlit app origin (e.g. `https://your-app.streamlit.app`) if the browser ever called the API directly; this client uses server-side `urllib`, so CORS does not apply to Streamlit’s requests, but your API may still need correct CORS for other clients.

## Verification

- Sidebar shows API health from `GET /api/health`.
- Complete a booking in the UI and confirm the **Booking summary** expander shows codes/ids when the API returns `booking_summary.kind == "booking_confirmed"`.
