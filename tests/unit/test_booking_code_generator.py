from src.domain.booking_code_generator import BookingCodeGenerator


def test_booking_code_format() -> None:
    generator = BookingCodeGenerator(exists_fn=lambda _: False)
    code = generator.generate()
    assert len(code) == 7
    assert code[2] == "-"


def test_booking_code_retries_on_collision(monkeypatch) -> None:
    generated = iter(["AB-C123", "ZX-Q111"])
    generator = BookingCodeGenerator(exists_fn=lambda c: c == "AB-C123")
    monkeypatch.setattr(generator, "_new_code", lambda: next(generated))
    assert generator.generate() == "ZX-Q111"


def test_booking_code_raises_after_max_retries(monkeypatch) -> None:
    generator = BookingCodeGenerator(exists_fn=lambda _: True, max_retries=2)
    monkeypatch.setattr(generator, "_new_code", lambda: "AB-C123")
    try:
        generator.generate()
        raise AssertionError("Expected unique-code generation to fail")
    except RuntimeError as exc:
        assert "unique booking code" in str(exc)

