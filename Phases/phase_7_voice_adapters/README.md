# Phase 7 — Voice Adapters (STT / TTS over Chat Runtime)

Boundary-only adapters that convert audio ↔ text without touching
orchestration, domain, or MCP logic.

## Architecture

```
Audio In ──► STT Adapter ──► Orchestrator.handle(text, session) ──► TTS Formatter ──► TTS Adapter ──► Audio Out
```

- **`config.py`** — loads voice feature flags and Google Cloud STT/TTS settings from `.env`.
- **`stt_adapter.py`** — Google Cloud Speech-to-Text; returns normalised text.
- **`tts_adapter.py`** — Google Cloud Text-to-Speech; returns audio bytes.
- **`tts_formatter.py`** — spoken-clarity transforms (booking codes, IST dates).
- **`chat_voice_bridge.py`** — glues STT → orchestrator → TTS in one call.

## Running tests

```bash
# from repo root
python -m pytest Phases/phase_7_voice_adapters/tests -q
```
