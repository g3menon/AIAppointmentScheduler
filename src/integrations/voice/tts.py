class TextToSpeech:
    def synthesize(self, assistant_message: str) -> bytes:
        # Adapter boundary only; does not implement business logic.
        raise NotImplementedError

