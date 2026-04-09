class SpeechToText:
    def transcribe(self, audio_chunk: bytes) -> str:
        # Adapter boundary only; does not implement business logic.
        raise NotImplementedError

