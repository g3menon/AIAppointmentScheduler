"""Google Cloud Text-to-Speech adapter.

Boundary adapter only — converts text to audio bytes.
No domain, orchestration, or MCP logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from phase7.config import VoiceConfig
from phase7.tts_formatter import chunk_text, format_for_speech


@dataclass
class TtsResult:
    """Output of a text-to-speech synthesis request."""

    audio_bytes: bytes
    audio_encoding: str
    char_count: int


class TtsClient(Protocol):
    """Abstraction so tests can substitute a fake without touching Google."""

    def synthesize(self, text: str, config: VoiceConfig) -> TtsResult: ...


class GoogleTtsAdapter:
    """Thin wrapper around ``google.cloud.texttospeech``."""

    def __init__(self) -> None:
        from google.cloud import texttospeech  # type: ignore[import-untyped]

        self._client = texttospeech.TextToSpeechClient()
        self._tts = texttospeech

    def synthesize(self, text: str, config: VoiceConfig) -> TtsResult:
        spoken = format_for_speech(text)

        encoding_map = {
            "MP3": self._tts.AudioEncoding.MP3,
            "LINEAR16": self._tts.AudioEncoding.LINEAR16,
            "OGG_OPUS": self._tts.AudioEncoding.OGG_OPUS,
        }
        audio_encoding = encoding_map.get(
            config.tts_audio_encoding, self._tts.AudioEncoding.MP3
        )

        voice = self._tts.VoiceSelectionParams(
            language_code=config.tts_language_code,
            name=config.tts_voice_name,
        )
        audio_config = self._tts.AudioConfig(
            audio_encoding=audio_encoding,
            speaking_rate=config.tts_speaking_rate,
            pitch=config.tts_pitch,
        )
        synthesis_input = self._tts.SynthesisInput(text=spoken)

        response = self._client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )
        return TtsResult(
            audio_bytes=response.audio_content,
            audio_encoding=config.tts_audio_encoding,
            char_count=len(spoken),
        )

    def synthesize_long(self, text: str, config: VoiceConfig) -> list[TtsResult]:
        """Chunk long text and synthesize each piece separately."""
        spoken = format_for_speech(text)
        chunks = chunk_text(spoken, config.max_assistant_chars_per_utterance)
        return [self.synthesize(c, config) for c in chunks]


class FakeTtsAdapter:
    """In-memory TTS stub for tests — records calls and returns dummy audio."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def synthesize(self, text: str, config: VoiceConfig) -> TtsResult:
        spoken = format_for_speech(text)
        self.calls.append(spoken)
        return TtsResult(
            audio_bytes=b"FAKE_AUDIO:" + spoken.encode("utf-8"),
            audio_encoding=config.tts_audio_encoding,
            char_count=len(spoken),
        )
