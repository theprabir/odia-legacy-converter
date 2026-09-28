"""
reverse_converter.py

Akruti → Unicode conversion engine.

Handles BOTH original Akruti output AND "fixed special chars" output
automatically. The user does not need to specify which type they have —
the converter detects and handles both transparently.

Akruti encoding is byte-level (latin-1). The conversion pipeline
(U→A) applies these transformations in order:

    1. NFC normalization
    2. Reph movement: ର୍ + CLUSTER → CLUSTER + ð
    3. Prebase matra movement: CLUSTER +େ → ù + CLUSTER
    4. JSON longest-match substitution → Akruti bytes

This reverse converter undoes them in reverse order:

    1. Reverse JSON longest-match → Unicode
    2. Undo prebase matra movement: ù + CLUSTER → CLUSTER +େ
    3. Undo reph movement: CLUSTER + ð → ର୍ + CLUSTER
    4. NFC normalization for clean rendering
"""

import json
import re
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

with open(
    BASE_DIR / "akruti_to_unicode.json", encoding="utf-8"
) as f:
    AKRUTI_TO_UNICODE = json.load(f)

# ------------------------------------------------------------------
# Sorted key list (longest first)
# ------------------------------------------------------------------

KEYS = sorted(
    AKRUTI_TO_UNICODE.keys(),
    key=len,
    reverse=True,
)

# ------------------------------------------------------------------
# Cluster byte detection
#
# In Akruti, a consonant cluster is: consonant + (halant + consonant)*
# We need to identify cluster bytes to parse prebase matra sequences.
# ------------------------------------------------------------------

# Single-byte consonants (map to Odia consonants)
_CONSONANT_BYTES = set(
    "KLMNOQRSTUVWXYZ[\\]^_`abcdefghijk"
)

# Multi-byte consonants: first_byte -> second_byte
_MULTI_CONSONANT = {
    "P": "\xff",   # Pÿ → ଚ
    "W": "\xff",   # Wÿ → ଡ଼
    "X": "\xff",   # Xÿ → ଢ଼
    "I": "\xdf",   # Iß → ୱ
}

# Halant+consonant single bytes (map to halant + consonant sequences)
_HALANT_CONSONANT_BYTES = set(
    "\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde"
    "\xa3\xe2\xe4\xe6\xe7\xe8"  # Ñ-Þ, £, â, ä, æ, ç, è
)

# Additional halant sequences (halant + consonant + matra)
_HALANT_SPECIAL_BYTES = set("\xe1\xee\xef")  # á, î, ï


def _is_cluster_byte(text, pos):
    """Check if the byte(s) at pos form part of a consonant cluster."""
    if pos >= len(text):
        return False

    ch = text[pos]

    # Single-byte consonant
    if ch in _CONSONANT_BYTES:
        return True

    # Multi-byte consonant (2 bytes)
    if ch in _MULTI_CONSONANT:
        expected = _MULTI_CONSONANT[ch]
        if pos + 1 < len(text) and text[pos + 1] == expected:
            return True

    # Halant byte þ — only a cluster byte if followed by a consonant
    if ch == "\xfe":
        return _is_cluster_byte(text, pos + 1)

    # Halant+consonant single byte
    if ch in _HALANT_CONSONANT_BYTES:
        return True

    # Special halant sequences (multi-byte)
    if ch in _HALANT_SPECIAL_BYTES:
        return True

    return False


def _cluster_byte_length(text, pos):
    """Return the byte length of the cluster unit at pos."""
    if pos >= len(text):
        return 0

    ch = text[pos]

    # Multi-byte consonant
    if ch in _MULTI_CONSONANT:
        expected = _MULTI_CONSONANT[ch]
        if pos + 1 < len(text) and text[pos + 1] == expected:
            return 2

    # Everything else is 1 byte if it's a cluster byte
    if _is_cluster_byte(text, pos):
        return 1

    return 0


# ------------------------------------------------------------------
# Dedicated whole-conjunct bytes.
#
# Many Akruti bytes represent an ENTIRE multi-consonant conjunct
# atomically (e.g. 'l' = "କ୍ଷ") rather than being built up from
# individual consonant + halant-continuation bytes. Because the
# forward converter's substitution step always takes the LONGEST
# available match, a prebase-matra's cluster is *always* represented
# by either (a) a base consonant plus zero or more halant-continuation
# bytes, or (b) exactly one such dedicated conjunct byte -- never a mix
# of the two. So when consuming a cluster we must also recognize these
# dedicated bytes as complete, non-extendable cluster units; otherwise
# words like "ନମସ୍ତେ"-shaped sequences (a dedicated conjunct byte
# immediately followed by a prebase e/ai/o/au matra) fail to round-trip.
# ------------------------------------------------------------------

_CONSONANT_CLASS_UNICODE = "କଖଗଘଙଚଛଜଝଞଟଠଡଢଣତଥଦଧନପଫବଭମଯରଲଳଶଷସହ" + "ଡ଼ଢ଼"

_DEDICATED_CONJUNCT_BYTES = {
    k for k, v in AKRUTI_TO_UNICODE.items()
    if len(k) == 1 and v and v[0] in _CONSONANT_CLASS_UNICODE
    and k not in _CONSONANT_BYTES
    and k not in _MULTI_CONSONANT
    and k not in _HALANT_CONSONANT_BYTES
    and k not in _HALANT_SPECIAL_BYTES
}


def _consume_cluster(text, start):
    """
    Consume a single Akruti consonant cluster starting at `start`:
    BASE consonant, followed by zero or more halant-joined
    continuations (either a dedicated halant+consonant byte such as
    'Ñ' = "୍କ", or an explicit halant byte 'þ' followed by a
    consonant) -- OR a single dedicated byte that represents an entire
    multi-consonant conjunct atomically (see _DEDICATED_CONJUNCT_BYTES).

    This mirrors the forward converter's CLUSTER regex
    (BASE (?:୍BASE)*) which only extends a cluster across an
    *explicit* halant. Unlike `_is_cluster_byte`, it does NOT treat
    a plain, unrelated base consonant that merely follows as part of
    the same cluster — that byte belongs to the *next* character.

    Returns the end position (exclusive). If no base consonant is
    found at `start`, returns `start` unchanged.
    """
    n = len(text)
    i = start

    if i >= n:
        return i

    ch = text[i]

    if ch in _DEDICATED_CONJUNCT_BYTES:
        return i + 1

    # First unit must be a base consonant (single or multi-byte).
    if ch in _MULTI_CONSONANT and i + 1 < n and text[i + 1] == _MULTI_CONSONANT[ch]:
        i += 2
    elif ch in _CONSONANT_BYTES:
        i += 1
    else:
        return start  # Not a cluster at all.

    # Extend across explicit halant-joined continuations only.
    while i < n:
        ch = text[i]

        # Dedicated single-byte halant+consonant unit (e.g. Ñ = "୍କ").
        if ch in _HALANT_CONSONANT_BYTES or ch in _HALANT_SPECIAL_BYTES:
            i += 1
            continue

        # Explicit halant byte þ, only if followed by a consonant.
        if ch == "\xfe":
            j = i + 1
            if j < n:
                ch2 = text[j]
                if ch2 in _MULTI_CONSONANT and j + 1 < n and text[j + 1] == _MULTI_CONSONANT[ch2]:
                    i = j + 2
                    continue
                if ch2 in _CONSONANT_BYTES:
                    i = j + 1
                    continue
            break

        break

    return i


# ------------------------------------------------------------------
# JSON-based longest-match substitution
# ------------------------------------------------------------------

def _json_substitute(text):
    """Convert Akruti bytes to Unicode using the reverse JSON mapping."""
    out = []
    i = 0

    while i < len(text):
        matched = False

        for k in KEYS:
            if text.startswith(k, i):
                out.append(AKRUTI_TO_UNICODE[k])
                i += len(k)
                matched = True
                break

        if not matched:
            out.append(text[i])
            i += 1

    return "".join(out)


# ------------------------------------------------------------------
# Prebase matra parsing
#
# Pattern: ù + CLUSTER + [÷|û|ø]?
#   ù + cluster        → cluster +େ  (e-matra)
#   ù + cluster + ÷    → cluster +ୈ  (ai-matra)
#   ù + cluster + û    → cluster +ୋ  (o-matra)
#   ù + cluster + ø    → cluster +ୌ  (au-matra)
# ------------------------------------------------------------------

_POSTBASE_MAP = {
    "\xf7": "\u0b48",  # ÷ → ୈ (ai-matra)
    "û": "\u0b4b",     # û → ୋ (o-matra)
    "\xf8": "\u0b4c",  # ø → ୌ (au-matra)
}

_E_MATRA = "\u0b47"  # େ (e-matra, no postbase marker)


def _parse_prebase_matra(text, start):
    """
    Parse a prebase matra sequence starting at 'start' (which points to ù).

    Returns (next_position, unicode_cluster_with_matra).
    """
    i = start + 1  # skip ù

    # --- Parse cluster bytes ---
    # Only consume ONE base consonant plus its explicit halant-joined
    # continuations — NOT any subsequent, unrelated base consonant
    # that simply happens to follow (see _consume_cluster).
    cluster_start = i
    i = _consume_cluster(text, i)
    cluster_akruti = text[cluster_start:i]

    # --- Check postbase marker ---
    matra = _E_MATRA  # default: e-matra

    if i < len(text):
        ch = text[i]
        if ch in _POSTBASE_MAP:
            matra = _POSTBASE_MAP[ch]
            i += 1
        # Special case: û as o-matra postbase.
        # 'û' is already in _POSTBASE_MAP, handled above.

    # --- Convert cluster to Unicode ---
    cluster_unicode = _json_substitute(cluster_akruti)

    return i, cluster_unicode + matra


# ------------------------------------------------------------------
# Main conversion
# ------------------------------------------------------------------

def convert_akruti_to_unicode(text: str) -> str:
    """
    Convert Akruti-encoded text to Unicode.

    Automatically handles both:
    - Original Akruti output (with ©, <, *, Î for certain conjuncts)
    - Fixed special chars output (with C1 control codes)

    Also correctly handles:
    - Prebase matras (e, ai, o, au) that were reordered in the
      forward conversion
    - Reph (re + halant) that was moved after its cluster

    Args:
        text: Akruti-encoded string (latin-1 byte sequences).

    Returns:
        Unicode Odia string.

    Raises:
        TypeError: If input is not a string.
    """
    if not isinstance(text, str):
        raise TypeError(
            f"convert_akruti_to_unicode() expects str, "
            f"got {type(text).__name__}"
        )

    if not text:
        return ""

    result = []
    i = 0

    while i < len(text):
        ch = text[i]

        # -----------------------------------------------------------
        # Prebase matra: ù + cluster + optional postbase
        # -----------------------------------------------------------
        if ch == "ù":
            i, unicode_seq = _parse_prebase_matra(text, i)
            result.append(unicode_seq)
            continue

        # -----------------------------------------------------------
        # Reph marker: ð after a cluster
        # Walk backward through result elements to find the consonant
        # cluster start, then prepend ର୍ to it.
        # -----------------------------------------------------------
        if ch == "ð":
            if result:
                j = len(result) - 1

                # Walk backward to find the start of the consonant
                # cluster that the reph attaches to.  A virama (୍)
                # can appear at the end of an element ("ଯ୍"), at the
                # start ("୍ୟ"), or as a standalone element ("୍").
                while j > 0:
                    if result[j - 1].endswith("୍"):
                        j -= 1
                    elif result[j].startswith("୍"):
                        j -= 1
                    else:
                        break

                result[j] = "ର୍" + result[j]
            i += 1
            continue

        # -----------------------------------------------------------
        # Regular: JSON longest-match substitution
        # -----------------------------------------------------------
        matched = False

        for k in KEYS:
            if text.startswith(k, i):
                result.append(AKRUTI_TO_UNICODE[k])
                i += len(k)
                matched = True
                break

        if not matched:
            result.append(ch)
            i += 1

    # ------------------------------------------------------------------
    # Post-processing: NFC normalization for clean rendering
    # ------------------------------------------------------------------
    converted = "".join(result)
    converted = unicodedata.normalize("NFC", converted)

    return converted
