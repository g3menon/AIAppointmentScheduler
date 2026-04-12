"""Unit tests for tts_formatter — spoken-clarity transforms."""

from __future__ import annotations

from phase7.tts_formatter import (
    chunk_text,
    format_for_speech,
    format_ist_datetime_spoken,
    spell_booking_code,
)


class TestSpellBookingCode:
    def test_standard_code(self):
        assert spell_booking_code("NL-A742") == "N. L. dash A. 7. 4. 2"

    def test_all_letters(self):
        assert spell_booking_code("AB-CDE") == "A. B. dash C. D. E"

    def test_all_digits_suffix(self):
        assert spell_booking_code("XY-1234") == "X. Y. dash 1. 2. 3. 4"

    def test_empty_string(self):
        assert spell_booking_code("") == ""


class TestFormatIstDatetimeSpoken:
    def test_dash_separator_replaced(self):
        result = format_ist_datetime_spoken("Mon 14 Apr 2025 10:00 – 10:30 IST")
        assert " to " in result
        assert "I.S.T." in result
        assert "–" not in result

    def test_plain_label_unchanged(self):
        label = "Tuesday afternoon"
        assert format_ist_datetime_spoken(label) == label


class TestFormatForSpeech:
    def test_booking_code_spelled_out(self):
        text = "Booking code: NL-A742."
        result = format_for_speech(text)
        assert "N. L. dash A. 7. 4. 2" in result

    def test_ist_replaced(self):
        result = format_for_speech("Your slot is 10:00 IST.")
        assert "I.S.T." in result
        assert "IST" not in result

    def test_bullets_stripped(self):
        text = "To prepare:\n- Have your ID\n- Note questions"
        result = format_for_speech(text)
        assert "- " not in result

    def test_newlines_become_pause(self):
        text = "Line one.\nLine two."
        result = format_for_speech(text)
        assert "..." in result

    def test_no_code_no_ist_passthrough(self):
        text = "Hello, how can I help?"
        assert format_for_speech(text) == text


class TestChunkText:
    def test_short_text_single_chunk(self):
        text = "Hello world."
        assert chunk_text(text, 500) == ["Hello world."]

    def test_long_text_split_on_sentence(self):
        s1 = "A" * 300 + "."
        s2 = "B" * 300 + "."
        text = f"{s1} {s2}"
        chunks = chunk_text(text, 400)
        assert len(chunks) == 2
        assert chunks[0] == s1
        assert chunks[1] == s2

    def test_single_very_long_sentence(self):
        text = "X" * 600
        chunks = chunk_text(text, 500)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_empty(self):
        assert chunk_text("", 500) == [""]
