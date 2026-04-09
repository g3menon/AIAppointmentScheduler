import random
import string


class BookingCodeGenerator:
    def __init__(self, exists_fn, max_retries: int = 5) -> None:
        self._exists_fn = exists_fn
        self._max_retries = max_retries

    def generate(self) -> str:
        for _ in range(self._max_retries):
            code = self._new_code()
            if not self._exists_fn(code):
                return code
        raise RuntimeError("Failed to generate unique booking code")

    def to_spelling(self, code: str) -> str:
        return " ".join(list(code.replace("-", " dash ")))

    @staticmethod
    def _new_code() -> str:
        prefix = "".join(random.choice(string.ascii_uppercase) for _ in range(2))
        letter = random.choice(string.ascii_uppercase)
        digits = "".join(random.choice(string.digits) for _ in range(3))
        return f"{prefix}-{letter}{digits}"

