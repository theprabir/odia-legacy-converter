"""
special_chars.py

Some Akruti-Sarala conjuncts (tta, nta, ncha, ...) are pre-built as a
single, dedicated glyph rather than assembled from separate consonant
glyphs joined by a halant. Those dedicated glyphs sit at Unicode
codepoints that render correctly on Windows 7/XP but as blank space on
Windows 10/11 with the identical font - a font/OS text-shaping
incompatibility, not a mapping error.

CONFIRMED via raw byte dump of jsahu.me's actual "Fix Extra Chars"
output (not copy-paste, which silently strips these - they are C1
control codepoints and get stripped by most browsers/text fields on
copy). jsahu.me's fix REPLACES each dedicated-ligature codepoint with a
different C1 control codepoint that the same font also has a working
glyph for; the destination byte still renders the correct Odia shape on
Windows 7/XP, but as a real (non-control) glyph rather than one modern
Unicode-aware renderers refuse to draw.

Confirmed mapping:
    U+00A9 '©' (ତ୍ତ, tta)   -> U+008F
    U+003C '<' (ଣ୍ଟ, nta)   -> U+008D
    U+002A '*' (ଞ୍ଚ, ncha)  -> U+0081
    

Only these 3 are confirmed. There are ~65 single-glyph two-consonant
conjuncts in unicode_to_akruti.json in total (see candidate_conjuncts())
- any others may or may not have the same problem, and even if they do,
their replacement byte is not guaranteed to follow a predictable
pattern. Confirm each one against real jsahu.me output (raw downloaded
file, not copy-paste) before adding it here.

IMPORTANT: the replacement characters are literal C1 control codepoints.
Any text containing them must be written to disk with an encoding that
preserves raw bytes 1:1 (this project uses Latin-1 throughout for
Akruti output - see desktop/ui/pages/converter_page.py download_output).
Do not route this text through UTF-8 export or plain-text web transport
without re-checking that the control bytes survive intact.
"""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

with open(BASE_DIR / "unicode_to_akruti.json", encoding="utf-8") as f:
    _TABLE = json.load(f)


# ------------------------------------------------------------------
# Confirmed via raw byte dump of jsahu.me's actual output.
# key = glyph as it appears in "Original" Akruti output
# value = the Windows 7/XP-correct replacement glyph
# ------------------------------------------------------------------
GLYPH_SUBSTITUTIONS = {
    "©": "\u008f",  # ତ୍ତ (tta)
    "<": "\u008d",  # ଣ୍ଟ (nta)
    "*": "\u0081",  # ଞ୍ଚ (ncha)
    "Î": "\u009d",  # ତ୍ଥ (ttha)
}


def candidate_conjuncts():
    """Return {unicode_conjunct: akruti_glyph} for every 2-consonant
    conjunct collapsed to a single dedicated Akruti byte - the category
    the confirmed substitutions are drawn from. Useful as a checklist
    for testing further glyphs against real jsahu.me output."""
    consonants = set(
        "କଖଗଘଙଚଛଜଝଞଟଠଡଢଣତଥଦଧନପଫବଭମଯରଲଳଵଶଷସହଡ଼ଢ଼ୟ"
    )
    halant = "୍"
    out = {}
    for uni_key, akruti_val in _TABLE.items():
        if (
            len(uni_key) == 3
            and uni_key[0] in consonants
            and uni_key[1] == halant
            and uni_key[2] in consonants
            and len(akruti_val) == 1
        ):
            out[uni_key] = akruti_val
    return out


def fix_special_characters(akruti_text: str, substitutions=None) -> str:
    """
    Replace known Windows-10/11-incompatible ligature glyphs with the
    Windows-7/XP-correct equivalent. Call this AFTER unicode_to_akruti(),
    not before - it operates on the Akruti byte stream, not the
    original Unicode text.
    """
    if not isinstance(akruti_text, str):
        raise TypeError(
            f"fix_special_characters() expects str, got {type(akruti_text).__name__}"
        )

    subs = substitutions if substitutions is not None else GLYPH_SUBSTITUTIONS
    if not subs:
        return akruti_text

    return "".join(subs.get(ch, ch) for ch in akruti_text)
