"""Round-trip test corpus.

Split into layers so failures point at a specific corpus slice:
- WORDS: real Odia words covering common conjuncts and matras
- LETTERS: consonants, vowels, matras, signs (single chars and CV syllables)
- CONJUNCTS: every 2-consonant single-glyph conjunct from the engine's table

Engine facts discovered while building this corpus. `converter_engine/` is
read-only, so per AGENTS.md Hard rule 1 they are documented here, not patched:

1. ASCII input passes through `convert_text`/`convert_text_sreelipi` unchanged
   ('a' -> 'a'), but `convert_akruti_to_unicode` maps ASCII bytes to Odia
   ('a' -> 'ବ', '0' -> '୦'). So ASCII does not round-trip through u2a+a2u;
   it is covered in TestAsciiConversion, excluded from the round-trip corpus.
2. 'ଵ' (Odia WA): u2a -> 'a', a2u('a') -> 'ବ'. No reverse entry. Asymmetric.
3. Nukta letters: u2a('କ଼') -> 'K' + U+0B3C (the combining nukta is passed
   through as a Unicode char, not an Akruti byte). U+0B3C is not
   cp1252-encodable, so a byte-level round trip cannot include nukta letters.
4. Sreelipi: 'ଙ', 'ଞ', 'ଵ', 'େ', 'ୈ', 'ୋ', 'ୌ', '଼' and the Odia digits
   pass through unchanged as Unicode (not converted to Sreelipi bytes).
   They are not cp1252-encodable, so the same exclusion applies.
5. Akruti output legitimately uses cp1252 code points *above* Latin-1's
   range (e.g. U+0192, U+2026, U+0152) which still encode to one cp1252
   byte. So no single 8-bit codec encodes ALL fixed-mode output:
   - cp1252 handles the >= U+0100 conjunct glyphs but not the C1 replacements;
   - latin-1 handles C1 but not the >= U+0100 glyphs.
   When both appear in one string (e.g. 'ତ୍ତଞ୍ଝ' fixed -> U+008F + U+0192)
   neither codec is lossless. The §6 "latin-1 for fixed" hypothesis holds
   only for pure C1 output. This needs an owner decision for /save (Phase 3);
   flagged, engine untouched.
"""

from __future__ import annotations

from typing import ClassVar

import pytest

from converter_engine import (
    convert_akruti_to_unicode,
    convert_sreelipi_to_unicode,
    convert_text,
    convert_text_sreelipi,
)
from converter_engine.special_chars import candidate_conjuncts

CONSONANTS = "କଖଗଘଙଚଛଜଝଞଟଠଡଢଣତଥଦଧନପଫବଭମଯରଲଳଶଷସହ"  # 'ଵ' excluded (fact 2)
VOWELS = "ଅଆଇଈଉଊଋଏଐଓଔ"
MATRAS = "ାିୀୁୂୃେୈୋୌ"
SIGNS = "ଂଃଁ"

WORDS: ClassVar[list[str]] = [
    # matra coverage
    "କାକି", "ପୁରୀ", "ଗୁରୁ", "ମାଟି", "କେଉଁ", "ପାଉଣି",
    # anusvara / visarga / chandrabindu
    "ଅଂଶ", "ଦୁଃଖ", "କାଁଆ",
    # conjuncts (incl. all four C1-producing ones in fixed mode)
    "ସତ୍ତର",      # ତ୍ତ -> \x8f fixed
    "ପଞ୍ଚାଶତ",    # ଞ୍ଚ -> \x81 fixed
    "କଣ୍ଟା",        # ଣ୍ଟ -> \x8d fixed
    "ଉତ୍ଥାନ",      # ତ୍ଥ -> \x9d fixed
    "କ୍ଷମା", "ଜ୍ଞାନ", "ଶ୍ରୀ", "ନମସ୍କାର", "ବିଦ୍ୟାଳୟ", "ସ୍ୱାଗତ",
    "ଆଶ୍ଚର୍ଯ୍ୟ", "ରଙ୍ଗ", "ଅନ୍ତରଙ୍ଗ", "ସମ୍ବାଦ", "ମିତ୍ର",
    # vocalic / special letters
    "ଋଷି", "ୟୟ",
]

ODIA_DIGITS = "୦୧୨୩୪୫୬୭୮୯"


def _corpus() -> list[str]:
    corpus = list(WORDS)
    corpus.append(ODIA_DIGITS)
    corpus.extend(CONSONANTS)
    corpus.extend(VOWELS)
    for c in CONSONANTS:
        corpus.append(c + "ା")
        corpus.append(c + "ି")
        corpus.append(c + "୍")
    for v in VOWELS:
        corpus.append("କ" + v)
    for m in MATRAS:
        corpus.append("କ" + m)
    corpus.extend("କ" + s for s in SIGNS)
    # All 65 two-consonant single-glyph conjuncts, standalone and with matras.
    corpus.extend(candidate_conjuncts())
    corpus.extend(c + "ଅ" for c in candidate_conjuncts())
    corpus.extend("ଅ" + c for c in candidate_conjuncts())
    return corpus


CORPUS: ClassVar[list[str]] = _corpus()


class TestAkrutiRoundtrip:
    """u2a -> cp1252 -> decode -> a2u must recover the original Odia text."""

    def test_corpus_roundtrip(self):
        for t in CORPUS:
            legacy = convert_text(t)
            data = legacy.encode("cp1252")  # must never raise
            assert convert_akruti_to_unicode(data.decode("cp1252")) == t, repr(t)


class TestSreelipiRoundtrip:
    """u2s -> cp1252 -> decode -> s2u must recover the original Odia text."""

    # Chars the Sreelipi engine passes through as Unicode instead of mapping
    # to legacy bytes; not cp1252-encodable, so no byte round trip is possible.
    PASSTHROUGH: ClassVar[frozenset[str]] = frozenset("ଙଞେୈୋୌ଼୦୧୨୩୪୫୬୭୮୯")

    def test_corpus_roundtrip(self):
        for t in CORPUS:
            if any(ch in self.PASSTHROUGH for ch in t):
                continue
            legacy = convert_text_sreelipi(t)
            data = legacy.encode("cp1252")  # must never raise
            assert convert_sreelipi_to_unicode(data.decode("cp1252")) == t, repr(t)

    def test_passthrough_chars_unchanged(self):
        for ch in self.PASSTHROUGH:
            assert convert_text_sreelipi(ch) == ch


class TestFixedModeC1:
    """Fixed-mode u2a: C1 appears exactly for the 4 confirmed conjuncts."""

    C1_PRODUCE: ClassVar[dict[str, str]] = {
        "ତ୍ତ": "\x8f",
        "ଞ୍ଚ": "\x81",
        "ଣ୍ଟ": "\x8d",
        "ତ୍ଥ": "\x9d",
    }
    C1_WORDS: ClassVar[list[str]] = ["ସତ୍ତର", "ପଞ୍ଚାଶତ", "କଣ୍ଟା", "ଉତ୍ଥାନ"]

    def test_confirmed_conjuncts_produce_expected_c1(self):
        for conj, cp in self.C1_PRODUCE.items():
            assert convert_text(conj, fix_special_chars=True) == cp

    def test_words_produce_expected_c1(self):
        for word, cp in zip(self.C1_WORDS, self.C1_PRODUCE.values()):
            fixed = convert_text(word, fix_special_chars=True)
            assert cp in fixed, (word, repr(fixed))

    def test_no_unexpected_c1_across_corpus(self):
        expected = set(self.C1_PRODUCE.values())
        for t in CORPUS:
            fixed = convert_text(t, fix_special_chars=True)
            stray = [c for c in fixed if 0x80 <= ord(c) <= 0x9F and c not in expected]
            assert not stray, (repr(t), [hex(ord(c)) for c in stray])

    def test_fixed_output_encodes_as_latin1_unless_high_glyphs(self):
        # §6 hypothesis "latin-1 for fixed output" holds only when the text
        # contains no >= U+0100 conjunct glyph (fact 5 in the module docstring).
        for t in CORPUS:
            fixed = convert_text(t, fix_special_chars=True)
            has_c1 = any(0x80 <= ord(c) <= 0x9F for c in fixed)
            has_high = any(ord(c) >= 0x100 for c in fixed)
            if has_c1 and has_high:
                continue  # no codec covers this; owner decision pending
            encoding = "latin-1" if has_c1 else "cp1252"
            fixed.encode(encoding)

    def test_mixed_c1_and_high_glyph_has_no_codec(self):
        # Demonstrates fact 5 on a minimal case; reported, not patched.
        fixed = convert_text("ତ୍ତଞ୍ଝ", fix_special_chars=True)
        assert fixed == "\x8fƒ"
        with pytest.raises(UnicodeEncodeError):
            fixed.encode("latin-1")
        with pytest.raises(UnicodeEncodeError):
            fixed.encode("cp1252")

    def test_fixed_mode_differs_only_on_c1_conjuncts(self):
        expected = set(self.C1_PRODUCE.values())
        for t in CORPUS:
            orig = convert_text(t)
            fixed = convert_text(t, fix_special_chars=True)
            if orig != fixed:
                changed = [c for c in fixed if c in expected]
                assert changed, repr(t)


class TestNoStrayHighCodepoints:
    """Legacy output must stay within cp1252-encodable range.

    Akruti/Sreelipi maps legitimately use code points above U+00FF (e.g.
    U+0192, U+2026, U+0152) that still encode to a single cp1252 byte, so the
    invariant is encodability, not `ord(c) < 0x100`.
    """

    def test_akruti_output_cp1252_encodable(self):
        for t in CORPUS:
            convert_text(t).encode("cp1252")  # must never raise

    def test_sreelipi_output_cp1252_encodable(self):
        for t in CORPUS:
            if any(ch in TestSreelipiRoundtrip.PASSTHROUGH for ch in t):
                continue
            convert_text_sreelipi(t).encode("cp1252")  # must never raise


class TestAsciiConversion:
    """ASCII input is converted, not preserved (verified engine behaviour)."""

    def test_ascii_passes_through_u2a(self):
        assert convert_text("a") == "a"
        assert convert_text("abc") == "abc"

    def test_ascii_does_not_survive_a2u(self):
        # a2u maps Akruti bytes to Odia unconditionally; 'abc' comes back
        # as 'ଇଈଉ ୟରଲ'-style Odia. Documented, not fixed (engine read-only).
        back = convert_akruti_to_unicode(convert_text("abc"))
        assert back != "abc"

    def test_plain_punctuation_roundtrips(self):
        # Punctuation the Akruti layout does not reuse survives intact.
        for t in ["! () . , ; : ? ", "+ - = /"]:
            assert convert_akruti_to_unicode(convert_text(t)) == t, repr(t)


class TestEngineAsymmetries:
    """Documented engine facts; reported per Hard rule 1, not patched."""

    def test_owa_letter_is_asymmetric(self):
        assert convert_text("ଵ") == "a"
        assert convert_akruti_to_unicode(convert_text("ଵ")) == "ବ"

    def test_nukta_is_passed_through_as_unicode(self):
        # Not cp1252-encodable -> cannot round-trip at byte level.
        out = convert_text("କ଼")
        assert "\u0b3c" in out

    def test_sreelipi_passes_through_some_chars_unchanged(self):
        for ch in "ଙଞେୈୋୌ":
            assert convert_text_sreelipi(ch) == ch


@pytest.mark.parametrize("text", CORPUS)
def test_corpus_parametrized_akruti(text):
    """Parametrized view of the same corpus for precise failure reporting."""
    legacy = convert_text(text)
    data = legacy.encode("cp1252")
    assert convert_akruti_to_unicode(data.decode("cp1252")) == text
