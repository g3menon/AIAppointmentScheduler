"""Chat ↔ Voice bridge: STT → Orchestrator.handle → TTS.

This module is the single integration point between voice adapters and the
chat runtime.  It **never** contains domain, MCP, or compliance logic — all
of that is delegated to ``Orchestrator.handle`` which already enforces PII
guard, disclaimer, and policy gates on the text path.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from phase7.config import VoiceConfig
from phase7.stt_adapter import FakeSttAdapter, SttClient, SttResult
from phase7.tts_adapter import FakeTtsAdapter, TtsClient, TtsResult
from phase7.tts_formatter import format_for_speech


@dataclass
class VoiceTurnResult:
    """Result of a single voice turn through the bridge."""

    stt_result: SttResult
    assistant_messages: list[str]
    tts_results: list[TtsResult]
    session_state: str
    errors: list[str] = field(default_factory=list)


class ChatVoiceBridge:
    """Wire: audio_in → STT → Orchestrator.handle(text) → TTS → audio_out.

    Parameters
    ----------
    orchestrator:
        The Phase 1 ``Orchestrator`` instance (``handle(text, session) → AgentTurn``).
    stt:
        Any object satisfying ``SttClient`` (``recognize(bytes, config) → SttResult``).
    tts:
        Any object satisfying ``TtsClient`` (``synthesize(text, config) → TtsResult``).
    config:
        Voice settings loaded from environment.
    """

    def __init__(
        self,
        orchestrator,
        stt: SttClient,
        tts: TtsClient,
        config: VoiceConfig,
    ) -> None:
        self._orch = orchestrator
        self._stt = stt
        self._tts = tts
        self._config = config

    def handle_audio(self, audio_bytes: bytes, session) -> VoiceTurnResult:
        """Process one voice turn end-to-end.

        1. STT converts *audio_bytes* → text.
        2. ``Orchestrator.handle`` runs the same chat path (PII guard,
           disclaimer, domain, MCP — unchanged).
        3. Each assistant message is formatted and sent through TTS.
        """
        errors: list[str] = []

        # --- STT ---------------------------------------------------------
        try:
            stt_result = self._stt.recognize(audio_bytes, self._config)
        except Exception as exc:
            errors.append(f"stt_error: {exc}")
            stt_result = SttResult(transcript="", confidence=0.0, is_final=True)

        if not stt_result.transcript:
            return VoiceTurnResult(
                stt_result=stt_result,
                assistant_messages=["I didn't catch that. Could you please repeat?"],
                tts_results=[],
                session_state=session.state.value if hasattr(session.state, "value") else str(session.state),
                errors=errors or ["stt_empty_transcript"],
            )

        # --- Orchestrator (same text path as chat) -----------------------
        turn = self._orch.handle(stt_result.transcript, session)

        # --- TTS ---------------------------------------------------------
        tts_results: list[TtsResult] = []
        for msg in turn.messages:
            try:
                result = self._tts.synthesize(msg, self._config)
                tts_results.append(result)
            except Exception as exc:
                errors.append(f"tts_error: {exc}")

        return VoiceTurnResult(
            stt_result=stt_result,
            assistant_messages=turn.messages,
            tts_results=tts_results,
            session_state=session.state.value if hasattr(session.state, "value") else str(session.state),
            errors=errors,
        )

    def handle_text_to_speech(self, text: str) -> TtsResult:
        """One-shot TTS for a pre-built assistant message (no STT/orchestrator)."""
        formatted = format_for_speech(text)
        return self._tts.synthesize(formatted, self._config)
