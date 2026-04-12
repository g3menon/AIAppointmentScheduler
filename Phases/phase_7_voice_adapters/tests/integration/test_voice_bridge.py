"""Integration tests: ChatVoiceBridge parity with text chat path.

Proves that audio-in → STT → Orchestrator.handle → TTS produces the same
assistant messages and state transitions as text-in → Orchestrator.handle.
Uses Fake STT/TTS so no Google Cloud credentials are required.
"""

from __future__ import annotations

import re

import pytest

from phase1.integrations.mcp.recording_client import RecordingGoogleMcpClient
from phase1.session.orchestrator import Orchestrator
from phase1.session.session_context import SessionContext
from phase1.session.state import State

from phase7.chat_voice_bridge import ChatVoiceBridge, VoiceTurnResult
from phase7.config import VoiceConfig
from phase7.stt_adapter import FakeSttAdapter
from phase7.tts_adapter import FakeTtsAdapter

_BOOKING_CODE_RE = re.compile(r"\b[A-Z]{2}-[A-Z0-9]{3,5}\b")


@pytest.fixture()
def voice_config() -> VoiceConfig:
    return VoiceConfig(
        enable_voice_api=True,
        enable_stt=True,
        enable_tts=True,
        google_cloud_project="test-project",
        stt_language_code="en-IN",
        stt_region="global",
        stt_model="latest_long",
        stt_audio_encoding="LINEAR16",
        stt_sample_rate_hz=16000,
        tts_language_code="en-IN",
        tts_voice_name="en-IN-Wavenet-D",
        tts_audio_encoding="MP3",
        tts_speaking_rate=1.0,
        tts_pitch=0.0,
        max_assistant_chars_per_utterance=500,
        store_raw_audio=False,
    )


def _run_text_turn(orch: Orchestrator, session: SessionContext, text: str):
    """Run a turn on the pure-text chat path and return the AgentTurn."""
    return orch.handle(text, session)


def _run_voice_turn(
    bridge: ChatVoiceBridge, session: SessionContext, text: str
) -> VoiceTurnResult:
    """Simulate a voice turn by feeding *text* through FakeSttAdapter."""
    return bridge.handle_audio(b"DUMMY_AUDIO", session)


class TestVoiceChatParity:
    """Voice bridge must produce the same messages and state as text chat."""

    def test_greeting_parity(self, voice_config: VoiceConfig):
        mcp = RecordingGoogleMcpClient()
        orch = Orchestrator(mcp_client=mcp)

        text_session = SessionContext(session_id="text-parity")
        voice_session = SessionContext(session_id="voice-parity")

        text_turn = _run_text_turn(orch, text_session, "hello")

        stt = FakeSttAdapter(transcript="hello")
        tts = FakeTtsAdapter()
        bridge = ChatVoiceBridge(orch, stt, tts, voice_config)
        voice_result = _run_voice_turn(bridge, voice_session, "hello")

        assert voice_result.assistant_messages == text_turn.messages
        assert voice_result.session_state == text_session.state.value

    def test_disclaimer_ack_parity(self, voice_config: VoiceConfig):
        mcp = RecordingGoogleMcpClient()
        orch = Orchestrator(mcp_client=mcp)

        text_session = SessionContext(session_id="text-disc")
        voice_session = SessionContext(session_id="voice-disc")

        _run_text_turn(orch, text_session, "hello")
        text_turn = _run_text_turn(orch, text_session, "yes")

        stt_hello = FakeSttAdapter(transcript="hello")
        tts = FakeTtsAdapter()
        bridge_hello = ChatVoiceBridge(orch, stt_hello, tts, voice_config)
        _run_voice_turn(bridge_hello, voice_session, "hello")

        stt_yes = FakeSttAdapter(transcript="yes")
        bridge_yes = ChatVoiceBridge(orch, stt_yes, tts, voice_config)
        voice_result = _run_voice_turn(bridge_yes, voice_session, "yes")

        assert voice_result.assistant_messages == text_turn.messages
        assert voice_result.session_state == text_session.state.value

    def test_full_booking_parity(self, voice_config: VoiceConfig):
        """Run a full booking transcript through both text and voice paths.

        Booking codes are random, so we normalise them before comparison.
        """
        turns = [
            "hello",
            "yes",
            "book",
            "KYC",
            "tomorrow morning",
            "1",
            "yes",
        ]

        mcp_text = RecordingGoogleMcpClient()
        orch_text = Orchestrator(mcp_client=mcp_text)
        text_session = SessionContext(session_id="text-book")

        mcp_voice = RecordingGoogleMcpClient()
        orch_voice = Orchestrator(mcp_client=mcp_voice)
        voice_session = SessionContext(session_id="voice-book")
        tts = FakeTtsAdapter()

        def _normalise(msgs: list[str]) -> list[str]:
            return [_BOOKING_CODE_RE.sub("XX-CODE", m) for m in msgs]

        for text in turns:
            text_turn = _run_text_turn(orch_text, text_session, text)

            stt = FakeSttAdapter(transcript=text)
            bridge = ChatVoiceBridge(orch_voice, stt, tts, voice_config)
            voice_result = _run_voice_turn(bridge, voice_session, text)

            assert _normalise(voice_result.assistant_messages) == _normalise(text_turn.messages), (
                f"Mismatch on turn '{text}': voice={voice_result.assistant_messages}, "
                f"text={text_turn.messages}"
            )
            assert voice_result.session_state == text_session.state.value

        assert text_session.state == State.CLOSE
        assert voice_session.state == State.CLOSE


class TestVoiceBridgeEdgeCases:
    """Edge-case handling in the bridge layer."""

    def test_empty_stt_transcript_gets_reprompt(self, voice_config: VoiceConfig):
        mcp = RecordingGoogleMcpClient()
        orch = Orchestrator(mcp_client=mcp)
        session = SessionContext(session_id="voice-empty")

        stt = FakeSttAdapter(transcript="", confidence=0.0)
        tts = FakeTtsAdapter()
        bridge = ChatVoiceBridge(orch, stt, tts, voice_config)
        result = bridge.handle_audio(b"silence", session)

        assert result.assistant_messages == [
            "I didn't catch that. Could you please repeat?"
        ]
        assert "stt_empty_transcript" in result.errors

    def test_stt_exception_handled_gracefully(self, voice_config: VoiceConfig):
        mcp = RecordingGoogleMcpClient()
        orch = Orchestrator(mcp_client=mcp)
        session = SessionContext(session_id="voice-stt-err")

        class BrokenStt:
            def recognize(self, audio_bytes, config):
                raise RuntimeError("Cloud unavailable")

        tts = FakeTtsAdapter()
        bridge = ChatVoiceBridge(orch, BrokenStt(), tts, voice_config)
        result = bridge.handle_audio(b"audio", session)

        assert any("stt_error" in e for e in result.errors)
        assert result.assistant_messages == [
            "I didn't catch that. Could you please repeat?"
        ]

    def test_tts_exception_handled_gracefully(self, voice_config: VoiceConfig):
        mcp = RecordingGoogleMcpClient()
        orch = Orchestrator(mcp_client=mcp)
        session = SessionContext(session_id="voice-tts-err")

        stt = FakeSttAdapter(transcript="hello")

        class BrokenTts:
            def synthesize(self, text, config):
                raise RuntimeError("TTS unavailable")

        bridge = ChatVoiceBridge(orch, stt, BrokenTts(), voice_config)
        result = bridge.handle_audio(b"audio", session)

        assert len(result.assistant_messages) > 0
        assert any("tts_error" in e for e in result.errors)
        assert result.tts_results == []

    def test_tts_results_match_messages(self, voice_config: VoiceConfig):
        mcp = RecordingGoogleMcpClient()
        orch = Orchestrator(mcp_client=mcp)
        session = SessionContext(session_id="voice-tts-count")

        stt = FakeSttAdapter(transcript="hello")
        tts = FakeTtsAdapter()
        bridge = ChatVoiceBridge(orch, stt, tts, voice_config)
        result = bridge.handle_audio(b"audio", session)

        assert len(result.tts_results) == len(result.assistant_messages)

    def test_pii_rejection_through_voice(self, voice_config: VoiceConfig):
        """PII guard must trigger identically in voice path (same orchestrator)."""
        mcp = RecordingGoogleMcpClient()
        orch = Orchestrator(mcp_client=mcp)
        session = SessionContext(session_id="voice-pii")

        stt = FakeSttAdapter(transcript="my phone number is 9876543210")
        tts = FakeTtsAdapter()
        bridge = ChatVoiceBridge(orch, stt, tts, voice_config)
        result = bridge.handle_audio(b"audio", session)

        assert any("personal identifiers" in m.lower() or "sensitive" in m.lower()
                    for m in result.assistant_messages)

    def test_investment_advice_refusal_through_voice(self, voice_config: VoiceConfig):
        mcp = RecordingGoogleMcpClient()
        orch = Orchestrator(mcp_client=mcp)
        session = SessionContext(session_id="voice-advice")

        stt = FakeSttAdapter(transcript="give me investment advice")
        tts = FakeTtsAdapter()
        bridge = ChatVoiceBridge(orch, stt, tts, voice_config)
        result = bridge.handle_audio(b"audio", session)

        assert any("investment advice" in m.lower() for m in result.assistant_messages)


class TestHandleTextToSpeech:
    """One-shot TTS helper (no STT or orchestrator involved)."""

    def test_returns_audio(self, voice_config: VoiceConfig):
        tts = FakeTtsAdapter()
        mcp = RecordingGoogleMcpClient()
        orch = Orchestrator(mcp_client=mcp)
        stt = FakeSttAdapter()
        bridge = ChatVoiceBridge(orch, stt, tts, voice_config)

        result = bridge.handle_text_to_speech("Your booking code is NL-A742.")
        assert result.audio_bytes
        assert result.char_count > 0
