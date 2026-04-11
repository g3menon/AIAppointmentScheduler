# Phase Folder Index

This folder tracks implementation scope by phase from `Docs/Architecture.md`.

**Canonical code and tests** live at the **repository root** in `src/` and `tests/`. Each `Phases/phase_*` folder is the scope checklist for that phase (not a second codebase).

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

Repository layout (single tree; see `Docs/Architecture.md` §11.3):
- `src/` — all phase implementations by seam (`api/chat`, `session`, `domain`, `nlu`, `integrations`, …)
- `tests/unit/` — deterministic logic
- `tests/integration/` — boundary handoffs
- `tests/e2e/` — full journeys (per Architecture §6.1)
- `Phases/phase_*/README.md` — scope and Definition of Done only

