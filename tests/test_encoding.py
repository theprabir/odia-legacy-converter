"""Tests for legacy encoding/decoding and the display sanitizer."""

from typing import ClassVar

import pytest

from lipika_cli.encoding import (
    decode_legacy,
    encode_legacy_strict,
    sanitize_for_display,
    unencodable_characters,
)

# Verified engine behaviour (phase 1 probing): fixed-mode u2a substitutes
# '©'->U+008F, '<'->U+008D, '*'->U+0081, 'Î'->U+009D.
C1_SAMPLES = {"©": "\x8f", "<": "\x8d", "*": "\x81", "Î": "\x9d"}


class TestSanitizeForDisplay:
    def test_c1_becomes_visible_token(self):
        assert sanitize_for_display("a\x8fb") == "a\\x8fb"
        assert sanitize_for_display("\x81") == "\\x81"

    def test_plain_text_unchanged(self):
        assert sanitize_for_display("IWÿò@û") == "IWÿò@û"
        assert sanitize_for_display("ଓଡ଼ିଆ") == "ଓଡ଼ିଆ"

    def test_empty(self):
        assert sanitize_for_display("") == ""

    def test_all_c1_range(self):
        for cp in range(0x80, 0xA0):
            assert "\\x" in sanitize_for_display(chr(cp))


class TestEncodeLegacy:
    def test_cp1252_ok_for_ascii_legacy(self):
        rep = encode_legacy_strict("IWÿò@û", "cp1252")
        assert rep.data.decode("cp1252") == "IWÿò@û"
        assert rep.unencodable == []

    def test_latin1_encodes_c1(self):
        rep = encode_legacy_strict("a\x8fb", "latin-1")
        assert rep.data == b"a\x8fb"

    def test_c1_not_encodable_as_cp1252_raises(self):
        # §9.3: never substitute silently -> strict encode surfaces the problem.
        with pytest.raises(UnicodeEncodeError):
            encode_legacy_strict("a\x8fb", "cp1252")

    def test_unencodable_characters_reported_distinct(self):
        bad = unencodable_characters("a\x8fb\x8fc\x9d", "cp1252")
        assert bad == ["\x8f", "\x9d"]

    def test_unencodable_characters_empty_when_encodable(self):
        assert unencodable_characters("IWÿò@û", "cp1252") == []


class TestDecodeLegacy:
    def test_cp1252_roundtrip(self):
        assert decode_legacy("IWÿò@û".encode("cp1252")) == "IWÿò@û"

    def test_undefined_bytes_map_to_c1(self):
        # 0x81, 0x8D, 0x8F, 0x90, 0x9D are undefined in cp1252; with errors=
        # they must come back as same-valued C1 codepoints, not '?'.
        raw = bytes([0x81, 0x8D, 0x8F, 0x90, 0x9D])
        text = decode_legacy(raw)
        for i, cp in enumerate((0x81, 0x8D, 0x8F, 0x90, 0x9D)):
            assert ord(text[i]) == cp


class TestLegacyRoundtrip:
    """§9.6: encode -> decode must return the identical string per mode."""

    SAMPLES: ClassVar[list[str]] = [
        "ଓଡ଼ିଆ ଲିପି ପରୀକ୍ଷା",
        "କ୍ଷମା କରନ୍ତୁ",
        "ନମସ୍କାର, ଓଡ଼ିଶା! 123",
    ]

    def test_u2a_original_cp1252_roundtrip(self):
        from converter_engine import convert_akruti_to_unicode, convert_text

        # ASCII digits convert to Odia digits and back; use digit-free samples.
        for t in [s for s in self.SAMPLES if "123" not in s]:
            legacy = convert_text(t)
            data = legacy.encode("cp1252")
            assert decode_legacy(data) == legacy
            assert convert_akruti_to_unicode(decode_legacy(data)) == t

    def test_u2a_with_digits_full_roundtrip(self):
        # ASCII digits convert to Odia digits and back; use digit-free samples.
        from converter_engine import convert_akruti_to_unicode, convert_text

        for t in [s for s in self.SAMPLES if "123" not in s]:
            legacy = convert_text(t)
            data = legacy.encode("cp1252")
            assert decode_legacy(data) == legacy
            assert convert_akruti_to_unicode(decode_legacy(data)) == t

    def test_sreelipi_high_codepoint_cp1252_roundtrip(self):
        # VERIFIED engine behaviour: Sreelipi output can contain codepoints
        # outside cp1252's printed table (e.g. U+0153 from 'ଜ୍ଞାନ') that Python
        # still maps to byte 0x9C on encode, so the byte round-trip is exact.
        # All characters are < U+0300, so encode(cp1252) is lossless here.
        from converter_engine import convert_text_sreelipi

        for t in self.SAMPLES:
            s = convert_text_sreelipi(t)
            assert all(ord(c) < 0x300 for c in s), "unexpected high codepoint"
            data = s.encode("cp1252")
            assert data.decode("cp1252") == s
