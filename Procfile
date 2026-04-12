# Heroku-style process file — used by Render, Railway, and similar hosts.
# PORT is set by the platform. Run from repository root.
web: uvicorn src.api.http.chat_app:app --host 0.0.0.0 --port ${PORT:-8000}
