from src.domain.booking_code_generator import BookingCodeGenerator


def test_booking_code_format() -> None:
    generator = BookingCodeGenerator(exists_fn=lambda _: False)
    code = generator.generate()
    assert len(code) == 7
    assert code[2] == "-"

