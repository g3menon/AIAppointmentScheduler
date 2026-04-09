# Phase 7 - Voice Adapters

## Required implementation files
- `src/integrations/voice/stt.py`
- `src/integrations/voice/tts.py`
- `src/api/voice/routes.py`
- `src/session/orchestrator.py` (unchanged contract only)

## Required tests
- `tests/integration/test_voice_pipeline.py`
- `tests/integration/test_chat_voice_parity.py`

## Checklist
- [ ] STT final utterance maps to same chat runtime call
- [ ] TTS reads each assistant message in order
- [ ] Barge-in does not bypass policy checks
- [ ] Raw audio/transcript persistence stays disabled by default

