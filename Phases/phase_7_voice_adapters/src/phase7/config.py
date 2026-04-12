"""Voice adapter configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class VoiceConfig:
    """Immutable snapshot of voice-related env settings."""

    enable_voice_api: bool
    enable_stt: bool
    enable_tts: bool

    google_cloud_project: str

    # STT
    stt_language_code: str
    stt_region: str
    stt_model: str
    stt_audio_encoding: str
    stt_sample_rate_hz: int

    # TTS
    tts_language_code: str
    tts_voice_name: str
    tts_audio_encoding: str
    tts_speaking_rate: float
    tts_pitch: float

    # UX / compliance
    max_assistant_chars_per_utterance: int
    store_raw_audio: bool


def load_voice_config() -> VoiceConfig:
    """Build a ``VoiceConfig`` from the current environment."""

    def _bool(key: str, default: str = "false") -> bool:
        return os.environ.get(key, default).strip().lower() in ("true", "1", "yes")

    def _int(key: str, default: str) -> int:
        return int(os.environ.get(key, default).strip())

    def _float(key: str, default: str) -> float:
        return float(os.environ.get(key, default).strip())

    def _str(key: str, default: str = "") -> str:
        return os.environ.get(key, default).strip()

    project = _str("GOOGLE_CLOUD_PROJECT") or _str("GOOGLE_PROJECT_ID")

    return VoiceConfig(
        enable_voice_api=_bool("ENABLE_VOICE_API"),
        enable_stt=_bool("ENABLE_STT"),
        enable_tts=_bool("ENABLE_TTS"),
        google_cloud_project=project,
        stt_language_code=_str("GOOGLE_STT_LANGUAGE_CODE", "en-IN"),
        stt_region=_str("GOOGLE_STT_REGION", "global"),
        stt_model=_str("GOOGLE_STT_MODEL", "latest_long"),
        stt_audio_encoding=_str("GOOGLE_STT_AUDIO_ENCODING", "LINEAR16"),
        stt_sample_rate_hz=_int("GOOGLE_STT_SAMPLE_RATE_HZ", "16000"),
        tts_language_code=_str("GOOGLE_TTS_LANGUAGE_CODE", "en-IN"),
        tts_voice_name=_str("GOOGLE_TTS_VOICE_NAME", "en-IN-Wavenet-D"),
        tts_audio_encoding=_str("GOOGLE_TTS_AUDIO_ENCODING", "MP3"),
        tts_speaking_rate=_float("GOOGLE_TTS_SPEAKING_RATE", "1.0"),
        tts_pitch=_float("GOOGLE_TTS_PITCH", "0.0"),
        max_assistant_chars_per_utterance=_int(
            "VOICE_MAX_ASSISTANT_CHARS_PER_UTTERANCE", "500"
        ),
        store_raw_audio=_bool("VOICE_STORE_RAW_AUDIO"),
    )
