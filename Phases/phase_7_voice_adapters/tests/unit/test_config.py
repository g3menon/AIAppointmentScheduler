"""Unit tests for VoiceConfig environment loading."""

from __future__ import annotations

import os
from unittest.mock import patch

from phase7.config import VoiceConfig, load_voice_config


class TestLoadVoiceConfig:
    def test_defaults_when_env_empty(self):
        with patch.dict(os.environ, {}, clear=True):
            cfg = load_voice_config()

        assert cfg.enable_voice_api is False
        assert cfg.enable_stt is False
        assert cfg.enable_tts is False
        assert cfg.stt_language_code == "en-IN"
        assert cfg.stt_sample_rate_hz == 16000
        assert cfg.tts_voice_name == "en-IN-Wavenet-D"
        assert cfg.tts_audio_encoding == "MP3"
        assert cfg.tts_speaking_rate == 1.0
        assert cfg.tts_pitch == 0.0
        assert cfg.max_assistant_chars_per_utterance == 500
        assert cfg.store_raw_audio is False

    def test_flags_enabled(self):
        env = {
            "ENABLE_VOICE_API": "true",
            "ENABLE_STT": "1",
            "ENABLE_TTS": "yes",
            "GOOGLE_CLOUD_PROJECT": "my-proj",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = load_voice_config()

        assert cfg.enable_voice_api is True
        assert cfg.enable_stt is True
        assert cfg.enable_tts is True
        assert cfg.google_cloud_project == "my-proj"

    def test_project_falls_back_to_google_project_id(self):
        env = {"GOOGLE_PROJECT_ID": "fallback-proj"}
        with patch.dict(os.environ, env, clear=True):
            cfg = load_voice_config()

        assert cfg.google_cloud_project == "fallback-proj"

    def test_custom_stt_settings(self):
        env = {
            "GOOGLE_STT_LANGUAGE_CODE": "en-US",
            "GOOGLE_STT_MODEL": "phone_call",
            "GOOGLE_STT_AUDIO_ENCODING": "FLAC",
            "GOOGLE_STT_SAMPLE_RATE_HZ": "44100",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = load_voice_config()

        assert cfg.stt_language_code == "en-US"
        assert cfg.stt_model == "phone_call"
        assert cfg.stt_audio_encoding == "FLAC"
        assert cfg.stt_sample_rate_hz == 44100

    def test_custom_tts_settings(self):
        env = {
            "GOOGLE_TTS_LANGUAGE_CODE": "en-US",
            "GOOGLE_TTS_VOICE_NAME": "en-US-Neural2-C",
            "GOOGLE_TTS_AUDIO_ENCODING": "OGG_OPUS",
            "GOOGLE_TTS_SPEAKING_RATE": "1.2",
            "GOOGLE_TTS_PITCH": "-2.5",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = load_voice_config()

        assert cfg.tts_language_code == "en-US"
        assert cfg.tts_voice_name == "en-US-Neural2-C"
        assert cfg.tts_audio_encoding == "OGG_OPUS"
        assert cfg.tts_speaking_rate == 1.2
        assert cfg.tts_pitch == -2.5

    def test_voice_config_is_frozen(self):
        cfg = VoiceConfig(
            enable_voice_api=True, enable_stt=True, enable_tts=True,
            google_cloud_project="p", stt_language_code="en-IN",
            stt_region="global", stt_model="latest_long",
            stt_audio_encoding="LINEAR16", stt_sample_rate_hz=16000,
            tts_language_code="en-IN", tts_voice_name="en-IN-Wavenet-D",
            tts_audio_encoding="MP3", tts_speaking_rate=1.0, tts_pitch=0.0,
            max_assistant_chars_per_utterance=500, store_raw_audio=False,
        )
        import pytest
        with pytest.raises(AttributeError):
            cfg.enable_voice_api = False  # type: ignore[misc]
