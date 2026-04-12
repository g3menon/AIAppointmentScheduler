"""Shared fixtures for Phase 7 voice adapter tests."""

from __future__ import annotations

import pytest

from phase7.config import VoiceConfig


@pytest.fixture()
def voice_config() -> VoiceConfig:
    """Deterministic VoiceConfig for unit tests (no env dependency)."""
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
