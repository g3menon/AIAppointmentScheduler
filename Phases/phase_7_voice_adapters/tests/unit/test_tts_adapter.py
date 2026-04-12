"""Unit tests for tts_adapter — TTS fake and contract."""

from __future__ import annotations

from phase7.config import VoiceConfig
from phase7.tts_adapter import FakeTtsAdapter, TtsResult


class TestFakeTtsAdapter:
    def test_returns_dummy_audio(self, voice_config: VoiceConfig):
        fake = FakeTtsAdapter()
        result = fake.synthesize("Hello world", voice_config)

        assert isinstance(result, TtsResult)
        assert result.audio_bytes.startswith(b"FAKE_AUDIO:")
        assert result.audio_encoding == "MP3"
        assert result.char_count > 0

    def test_records_calls(self, voice_config: VoiceConfig):
        fake = FakeTtsAdapter()
        fake.synthesize("First message", voice_config)
        fake.synthesize("Second message", voice_config)
        assert len(fake.calls) == 2

    def test_applies_format_for_speech(self, voice_config: VoiceConfig):
        fake = FakeTtsAdapter()
        result = fake.synthesize("Booking code: NL-A742.", voice_config)
        assert b"N. L. dash A. 7. 4. 2" in result.audio_bytes

    def test_ist_reformatted(self, voice_config: VoiceConfig):
        fake = FakeTtsAdapter()
        result = fake.synthesize("Your slot is 10:00 IST.", voice_config)
        assert b"I.S.T." in result.audio_bytes


class TestTtsResult:
    def test_dataclass_fields(self):
        r = TtsResult(audio_bytes=b"audio", audio_encoding="MP3", char_count=5)
        assert r.audio_bytes == b"audio"
        assert r.audio_encoding == "MP3"
        assert r.char_count == 5
