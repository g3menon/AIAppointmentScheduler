"""Google Cloud Speech-to-Text adapter.

Boundary adapter only — converts audio bytes to normalised text.
No domain, orchestration, or MCP logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from phase7.config import VoiceConfig


@dataclass
class SttResult:
    """Normalised output of a speech-to-text recognition request."""

    transcript: str
    confidence: float
    is_final: bool


class SttClient(Protocol):
    """Abstraction so tests can substitute a fake without touching Google."""

    def recognize(self, audio_bytes: bytes, config: VoiceConfig) -> SttResult: ...


class GoogleSttAdapter:
    """Thin wrapper around ``google.cloud.speech``."""

    def __init__(self) -> None:
        from google.cloud import speech  # type: ignore[import-untyped]

        self._client = speech.SpeechClient()
        self._speech = speech

    def recognize(self, audio_bytes: bytes, config: VoiceConfig) -> SttResult:
        encoding_map = {
            "LINEAR16": self._speech.RecognitionConfig.AudioEncoding.LINEAR16,
            "FLAC": self._speech.RecognitionConfig.AudioEncoding.FLAC,
            "MP3": self._speech.RecognitionConfig.AudioEncoding.MP3,
            "OGG_OPUS": self._speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
        }
        encoding = encoding_map.get(
            config.stt_audio_encoding,
            self._speech.RecognitionConfig.AudioEncoding.LINEAR16,
        )

        recognition_config = self._speech.RecognitionConfig(
            encoding=encoding,
            sample_rate_hertz=config.stt_sample_rate_hz,
            language_code=config.stt_language_code,
            model=config.stt_model,
            enable_automatic_punctuation=True,
        )
        audio = self._speech.RecognitionAudio(content=audio_bytes)

        response = self._client.recognize(config=recognition_config, audio=audio)

        if not response.results:
            return SttResult(transcript="", confidence=0.0, is_final=True)

        best = response.results[0].alternatives[0]
        return SttResult(
            transcript=best.transcript.strip(),
            confidence=best.confidence,
            is_final=response.results[0].is_final
            if hasattr(response.results[0], "is_final")
            else True,
        )


class FakeSttAdapter:
    """In-memory STT stub for tests — returns a pre-configured transcript."""

    def __init__(self, transcript: str = "", confidence: float = 0.95) -> None:
        self._transcript = transcript
        self._confidence = confidence
        self.last_audio: bytes | None = None

    def recognize(self, audio_bytes: bytes, config: VoiceConfig) -> SttResult:
        self.last_audio = audio_bytes
        return SttResult(
            transcript=self._transcript,
            confidence=self._confidence,
            is_final=True,
        )
