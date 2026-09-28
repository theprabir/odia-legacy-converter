"""
Sreelipi -> Unicode Odia reverse converter.

Mirrors the structure documented in sreelipi_reorder.py (see that file
for the encoding scheme). Reverse conversion is simpler than Akruti's:
almost every Sreelipi byte maps to a complete, atomic Unicode conjunct
already (no partial cluster-building is needed), so the bulk of the work
is a straight substitution. The two structural pieces that DO need
reordering are the prebase e/ai/o/au marker "{" and the reph markers
"ö" / "}".

Special-character-glyph note (the Sreelipi analogue of Akruti's C1 issue):
Sreelipi uses the Windows-1252 codepage's 0x80-0x9F range for several
common conjuncts and punctuation marks (†, ™, ', ", •, ‡, Š, œ, Ÿ, etc.)
instead of plain Latin-1/C1 control codes. Depending on how a document
was saved/copied, those same underlying byte values can arrive either as
their CP1252 character (the common case, handled directly by the main
table) or as raw C1 control codepoints U+0080-U+009F (if the text passed
through a pure Latin-1 step somewhere). `_normalize_c1_to_cp1252` below
converts the latter into the former before the main substitution runs,
so both variants convert correctly.
"""

import json
import re
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

with open(BASE_DIR / "sreelipi_to_unicode.json", encoding="utf-8") as f:
    SREELIPI_TO_UNICODE = json.load(f)

# Multi-char legacy input variants (checked before the single-char table).
# Order matters only when two keys overlap at the same position; the
# longest keys are listed first.
_MULTI_CHAR_INPUT = {
    # word-final halant followed by the em-dash escape: the halant byte
    # + blank + dash must recombine BEFORE "úÿ" eats the blank.  The
    # replacement keeps a blank so _substitute's "ÿ—" lookahead restores
    # the dash instead of the single-byte "—"->ଦ୍ଭୁ rule firing.
    "úÿ—": "୍ÿ—",
    "úÿ": "୍\u200c",  # halant + ZWNJ (the real Sreelipi word-final-halant form)
    "H´": "ୱ",  # va (U+0B71) is a dedicated two-byte sequence, per the
    #                 Font-Exchange/OdiaWikimedia converters
    "oe": "ନ",
    "þ#": "ତ୍ମ",
}

PREBASE_MARK = "{"
AI_EXTRA = "ð"
O_EXTRA = "ା"   # aa-matra glyph, already substituted by the time this runs
AU_EXTRA = "ò"
REPH_MARK_1 = "ö"
REPH_MARK_2 = "}"  # reph + implicit i-matra (font-specific glyph quirk)

# ୱ (U+0B71) is included so prebase-matra markers ("{") and reph can
# move across clusters containing va (e.g. ସଫ୍ଟୱେର), mirroring the
# forward converter's cluster definition.
CONSONANT_CLASS = "କଖଗଘଙଚଛଜଝଞଟଠଡଡ଼ଢଢ଼ଣତଥଦଧନପଫବଭମଯରଲଳବଶଷସହୱ" + "ୟ"
MATRA_CLASS = "ାିୀୁୂୃେୈୋୌଂଁ"

_CLUSTER = rf"[{CONSONANT_CLASS}](?:୍[{CONSONANT_CLASS}])*"

# "{" followed by a WHOLE consonant cluster (including ୱ clusters like
# ସଫ୍ଟୱ): the marker must hop over the entire cluster in one go, or it
# strands in the middle for clusters whose first consonant isn't itself
# halant-joined (e.g. ସଫ୍ଟୱ -> ସେଫ୍ଟୱ instead of ସଫ୍ଟୱେ).
_RE_PREBASE_MOVE_ALL = re.compile(rf"(\{{)({_CLUSTER})")
# Fallbacks for marker positions the whole-cluster regex can't see (e.g.
# "{" typed mid-cluster, directly before a halant): single-consonant hop
# and halant+consonant hop, mirroring the real converters' regexes.
_RE_PREBASE_MOVE_1 = re.compile(rf"(\{{)([{CONSONANT_CLASS}])")
_RE_PREBASE_MOVE_2 = re.compile(rf"(\{{)(୍)([{CONSONANT_CLASS}])")
_RE_PREBASE_AI = re.compile(r"\{ð")
_RE_PREBASE_O = re.compile(r"\{ା")
_RE_PREBASE_AU = re.compile(r"\{ò")

# Reph must move past the WHOLE preceding consonant cluster (which may
# be joined by one or more halants, e.g. "ନ୍ତ୍ର"), not just a single
# trailing consonant -- otherwise reph on a 2+-halant cluster like
# "ର୍ନ୍ତ୍ର" lands in the middle instead of at the start.
_RE_REPH1_MOVE = re.compile(rf"({_CLUSTER})([{MATRA_CLASS}]*)ö")
_RE_REPH2_MOVE = re.compile(rf"({_CLUSTER})([{MATRA_CLASS}]*)\}}")


# ------------------------------------------------------------------
# C1 control-codepoint normalization (special-character-glyph fix)
# ------------------------------------------------------------------

_C1_TO_CP1252 = {}
for _byte in range(0x80, 0xA0):
    try:
        _ch = bytes([_byte]).decode("cp1252")
    except UnicodeDecodeError:
        continue
    _C1_TO_CP1252[chr(_byte)] = _ch


def _normalize_c1_to_cp1252(text: str) -> str:
    if not any(ch in _C1_TO_CP1252 for ch in text):
        return text
    return "".join(_C1_TO_CP1252.get(ch, ch) for ch in text)


# ------------------------------------------------------------------
# Multi-char substitution pass (legacy variants)
# ------------------------------------------------------------------

def _substitute_multi_char(text: str) -> str:
    for key, val in _MULTI_CHAR_INPUT.items():
        text = text.replace(key, val)
    return text


# ------------------------------------------------------------------
# Main single-char substitution
# ------------------------------------------------------------------

def _substitute(text: str) -> str:
    out = []
    i = 0
    n = len(text)
    table = SREELIPI_TO_UNICODE
    while i < n:
        ch = text[i]
        # Em-dash escape: the forward converter carries the Unicode em
        # dash as blank+"—" because the raw "—" byte is really the ଦ୍ଭୁ
        # conjunct in the Sreelipi font.  Restore it before the single-
        # byte lookup would turn "—" into ଦ୍ଭୁ.
        if ch == "ÿ" and i + 1 < n and text[i + 1] == "—":
            out.append("—")
            i += 2
            continue
        out.append(table.get(ch, ch))
        i += 1
    return "".join(out)


# ------------------------------------------------------------------
# Prebase matra + reph reordering (post-substitution, mirrors the
# verified OdiaWikimedia reorder regexes)
# ------------------------------------------------------------------

def _move_prebase_matras(text: str) -> str:
    # Move "{" past the whole following consonant cluster (handles
    # clusters of any length, incl. ୱ clusters).  The single- and
    # halant+consonant hops are only fallbacks for hand-typed marker
    # positions the whole-cluster regex cannot see (e.g. "{" typed
    # directly before a halant) -- they must NOT run when the
    # whole-cluster regex already moved a marker, or a correctly placed
    # marker gets re-moved (ଶ୍ରେଣୀ -> ଶ୍ରଣେୀ).
    text, n_all = _RE_PREBASE_MOVE_ALL.subn(r"\2\1", text)
    if not n_all:
        text, n_1 = _RE_PREBASE_MOVE_1.subn(r"\2\1", text)
        if not n_1:
            text = _RE_PREBASE_MOVE_2.sub(r"\2\3\1", text)
            text = _RE_PREBASE_MOVE_2.sub(r"\2\3\1", text)

    text = _RE_PREBASE_AI.sub("ୈ", text)
    text = _RE_PREBASE_O.sub("ୋ", text)
    text = _RE_PREBASE_AU.sub("ୌ", text)
    text = text.replace(PREBASE_MARK, "େ")

    # Anusvara/chandrabindu typed before a matra must follow it in
    # logical Unicode order.
    text = re.sub(r"([ଂଁ])([ାିୀୁୂୃେୈୋୌ])", r"\2\1", text)

    return text


def _move_reph(text: str) -> str:
    text = _RE_REPH1_MOVE.sub(r"ö\1\2", text)
    text = text.replace(REPH_MARK_1, "ର୍")

    text = _RE_REPH2_MOVE.sub(r"}\1\2ି", text)
    text = text.replace(REPH_MARK_2, "ର୍")

    return text


# ------------------------------------------------------------------
# Public entry point
# ------------------------------------------------------------------

def convert_sreelipi_to_unicode(text):
    if text is None:
        return ""

    if not isinstance(text, str):
        raise TypeError(f"convert_sreelipi_to_unicode() expects str, got {type(text).__name__}")

    text = _normalize_c1_to_cp1252(text)
    text = _substitute_multi_char(text)
    text = _substitute(text)
    text = _move_prebase_matras(text)
    text = _move_reph(text)
    text = text.replace("ଅା", "ଆ")  # collapse decomposed aa (Sreelipi types ଆ as A+æ)
    text = unicodedata.normalize("NFC", text)

    return text
