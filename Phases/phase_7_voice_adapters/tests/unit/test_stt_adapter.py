"""Unit tests for stt_adapter — STT fake and contract."""

from __future__ import annotations

from phase7.config import VoiceConfig
from phase7.stt_adapter import FakeSttAdapter, SttResult


class TestFakeSttAdapter:
    def test_returns_configured_transcript(self, voice_config: VoiceConfig):
        fake = FakeSttAdapter(transcript="book appointment", confidence=0.92)
        result = fake.recognize(b"\x00\x01", voice_config)

        assert isinstance(result, SttResult)
        assert result.transcript == "book appointment"
        assert result.confidence == 0.92
        assert result.is_final is True

    def test_records_audio_bytes(self, voice_config: VoiceConfig):
        fake = FakeSttAdapter(transcript="hello")
        audio = b"\xff" * 100
        fake.recognize(audio, voice_config)
        assert fake.last_audio == audio

    def test_empty_transcript(self, voice_config: VoiceConfig):
        fake = FakeSttAdapter(transcript="", confidence=0.0)
        result = fake.recognize(b"", voice_config)
        assert result.transcript == ""
        assert result.confidence == 0.0


class TestSttResult:
    def test_dataclass_fields(self):
        r = SttResult(transcript="hello", confidence=0.9, is_final=True)
        assert r.transcript == "hello"
        assert r.confidence == 0.9
        assert r.is_final is True
