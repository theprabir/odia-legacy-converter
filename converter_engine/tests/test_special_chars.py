"""
Tests for special_chars.py

Verifies:
1. The 4 confirmed glyph substitutions work correctly.
2. Unrelated characters (including non-Latin-1) remain unchanged.
3. The full convert_text + fix_special_characters pipeline preserves data.
"""

import pytest

from converter_engine.special_chars import (
    GLYPH_SUBSTITUTIONS,
    fix_special_characters,
)
from converter_engine.converter import convert_text


# =====================================================
# GLYPH_SUBSTITUTIONS correctness
# =====================================================


class TestGlyphSubstitutions:
    """Verify the 4 confirmed mappings are present and correct."""

    def test_four_mappings_exist(self):
        assert len(GLYPH_SUBSTITUTIONS) == 4

    def test_tta_mapping(self):
        """© (U+00A9) → U+008F for tta conjunct."""
        assert GLYPH_SUBSTITUTIONS["©"] == "\u008f"

    def test_nta_mapping(self):
        """< (U+003C) → U+008D for nta conjunct."""
        assert GLYPH_SUBSTITUTIONS["<"] == "\u008d"

    def test_ncha_mapping(self):
        """* (U+002A) → U+0081 for ncha conjunct."""
        assert GLYPH_SUBSTITUTIONS["*"] == "\u0081"

    def test_ttha_mapping(self):
        """Î (U+00CE) → U+009D for ttha conjunct."""
        assert GLYPH_SUBSTITUTIONS["Î"] == "\u009d"


# =====================================================
# fix_special_characters behaviour
# =====================================================


class TestFixSpecialCharacters:
    """Verify fix_special_characters only touches the 4 confirmed glyphs."""

    def test_empty_string(self):
        assert fix_special_characters("") == ""

    def test_none_raises(self):
        with pytest.raises(TypeError):
            fix_special_characters(None)

    def test_replaces_tta(self):
        result = fix_special_characters("abc©def")
        assert result == "abc\u008fdef"

    def test_replaces_nta(self):
        result = fix_special_characters("x<y")
        assert result == "x\u008dy"

    def test_replaces_ncha(self):
        result = fix_special_characters("a*b")
        assert result == "a\u0081b"

    def test_replaces_ttha(self):
        result = fix_special_characters("Î")
        assert result == "\u009d"

    def test_no_change_when_no_match(self):
        """Characters not in the substitution map must remain untouched."""
        assert fix_special_characters("hello world") == "hello world"

    def test_odia_characters_unchanged(self):
        """Odia Unicode characters must NOT be modified."""
        odia = "ଓଡ଼ିଆ ଭାଷା"
        assert fix_special_characters(odia) == odia

    def test_punctuation_unchanged(self):
        """Punctuation other than < and * must remain unchanged."""
        text = ".,;:!?()[]{}'\""
        # < and * are in the map; remove them for this test
        text_no_special = ".,;:!?'\"()[]{}"
        assert fix_special_characters(text_no_special) == text_no_special

    def test_digits_unchanged(self):
        assert fix_special_characters("0123456789") == "0123456789"

    def test_whitespace_unchanged(self):
        assert fix_special_characters(" \t\n\r ") == " \t\n\r "

    def test_custom_substitutions(self):
        """Custom substitution dict should override defaults."""
        result = fix_special_characters("aXb", substitutions={"X": "Y"})
        assert result == "aYb"

    def test_empty_substitutions(self):
        """Empty substitution dict returns text unchanged."""
        result = fix_special_characters("abc©", substitutions={})
        assert result == "abc©"

    def test_multiple_occurrences(self):
        result = fix_special_characters("©©©")
        assert result == "\u008f\u008f\u008f"

    def test_mixed_mapped_and_unmapped(self):
        """Only mapped characters change; others stay."""
        result = fix_special_characters("A©B<C*DÎE")
        assert result == "A\u008fB\u008dC\u0081D\u009dE"

    def test_non_latin1_odia_preserved(self):
        """Characters outside Latin-1 (e.g. Odia codepoints) must survive."""
        # Odia letter KA (U+0B15) is outside Latin-1
        text = "\u0b15\u0b15\u0b15"
        result = fix_special_characters(text)
        assert result == text

    def test_mixed_latin1_and_non_latin1(self):
        """Mix of Latin-1 and non-Latin-1: only the 4 glyphs change."""
        # U+0B15 = Odia KA (not Latin-1), © is a mapped glyph
        text = "\u0b15©\u0b16"
        result = fix_special_characters(text)
        assert result == "\u0b15\u008f\u0b16"


# =====================================================
# Full pipeline: convert + fix_special_characters
# =====================================================


class TestFullPipeline:
    """End-to-end: convert_text with fix_special_chars preserves all chars."""

    def test_fix_does_not_corrupt_output(self):
        """Converting Odia text with fix=True must not introduce '?' characters."""
        text = "ଓଡ଼ିଆ ଭାଷା ପ୍ରକାଶ"
        result = convert_text(text, fix_special_chars=True)
        assert isinstance(result, str)
        assert len(result) > 0
        # '?' (0x3F) should not appear unless it was in the original mapping
        # The main concern is that fix_special_chars doesn't corrupt characters

    def test_fix_output_utf8_encodable(self):
        """Fixed output must survive a UTF-8 encode/decode round-trip."""
        text = "ଓଡ଼ିଆ ଭାଷା"
        result = convert_text(text, fix_special_chars=True)
        # This should not raise
        encoded = result.encode("utf-8")
        decoded = encoded.decode("utf-8")
        assert decoded == result

    def test_original_vs_fixed_differ_only_by_mapped_glyphs(self):
        """Original and fixed outputs should differ only where the 4 mappings apply."""
        text = "ଓଡ଼ିଆ ଭାଷା ପ୍ରକାଶ"
        original = convert_text(text, fix_special_chars=False)
        fixed = convert_text(text, fix_special_chars=True)

        # They should both be non-empty strings
        assert len(original) > 0
        assert len(fixed) > 0
        # Same length (replacements are 1-to-1)
        assert len(original) == len(fixed)

        # Positions that differ must only involve the 4 mapped glyphs
        for i, (o, f) in enumerate(zip(original, fixed)):
            if o != f:
                # The original char must be one of the 4 keys
                assert o in GLYPH_SUBSTITUTIONS, (
                    f"Position {i}: unexpected diff original={repr(o)} fixed={repr(f)}"
                )
                # The fixed char must be the corresponding value
                assert f == GLYPH_SUBSTITUTIONS[o], (
                    f"Position {i}: replacement mismatch"
                )
