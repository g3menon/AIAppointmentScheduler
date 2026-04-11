# Phase Folder Index

This folder tracks implementation scope by phase from `Docs/Architecture.md`.

- **Phase 1** is self-contained under `Phases/phase_1_chat_runtime/` (Python package `phase1`, tests beside it). Root `src/api/chat/routes.py` re-exports the Phase 1 chat API for convenience.
- **Phases 2+** continue to use the shared root `src/` tree and `tests/` as work proceeds.

- `phase_1_chat_runtime/`
- `phase_2_domain_logic/`
- `phase_3_nlu_and_mcp/`
- `phase_4_reliability_observability/`
- `phase_5_waitlist_and_advice_policy/`
- `phase_6_secondary_intents/`
- `phase_7_voice_adapters/`
- `phase_8_hardening_ops/`

Each phase folder has:
- required modules (paths relative to repo root unless noted)
- expected tests
- completion checklist

Repository layout (see `Docs/Architecture.md` §11.3):
- `Phases/phase_1_chat_runtime/src/phase1/` — Phase 1 chat runtime + compliance
- `Phases/phase_1_chat_runtime/tests/` — Phase 1 unit / integration / e2e
- `src/` — shared seams for Phase 2+ (`domain`, `nlu`, `integrations/google_mcp`, …); thin chat re-export for Phase 1
- `tests/` — tests for root `src/` (e.g. Phase 2 modules as they land)
- `Phases/phase_*/README.md` — scope and Definition of Done

Run Phase 1 tests from repo root: `pytest` (root `pytest.ini` includes both test trees), or only Phase 1: `pytest Phases/phase_1_chat_runtime/tests` with `Phases/phase_1_chat_runtime/pytest.ini`.

