import re

_PHONE = re.compile(r"\b\d{10}\b")
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_ACCOUNT = re.compile(r"\b(?:\d[ -]?){12,16}\b")


def contains_pii(text: str) -> bool:
    return bool(_PHONE.search(text) or _EMAIL.search(text) or _ACCOUNT.search(text))
