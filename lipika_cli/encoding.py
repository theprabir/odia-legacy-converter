"""Legacy single-byte encode/decode and terminal display sanitizer."""

from __future__ import annotations

from dataclasses import dataclass

# Characters undefined in cp1252 (bytes 0x81, 0x8D, 0x8F, 0x90, 0x9D); they map
# to the same-valued C1 codepoints on decode.
_UNDEFINED_CP1252 = frozenset("\x81\x8d\x8f\x90\x9d")


@dataclass(frozen=True)
class EncodeReport:
    """Outcome of encoding a legacy string for saving."""

    data: bytes
    unencodable: list[str]  # distinct characters that could not be encoded
    substituted: bool  # True when unencodable chars were written as '?'


def encode_legacy_strict(text: str, encoding: str) -> EncodeReport:
    """Encode without any substitution.

    Raises UnicodeEncodeError if `text` is not encodable; callers that want a
    file anyway must follow up with `encode_legacy_substituting` after
    reporting the offending characters (§9.3: never substitute silently).
    """
    data = text.encode(encoding, errors="strict")
    return EncodeReport(data=data, unencodable=[], substituted=False)


def unencodable_characters(text: str, encoding: str) -> list[str]:
    """Distinct characters of `text` that `encoding` cannot represent."""
    bad: list[str] = []
    for ch in text:
        try:
            ch.encode(encoding)
        except UnicodeEncodeError:
            if ch not in bad:
                bad.append(ch)
    return bad


def encode_legacy_substituting(text: str, encoding: str) -> EncodeReport:
    """Encode with '?' in place of unencodable characters.

    Only call after the caller has surfaced a warning listing
    `unencodable_characters` (§9.3).
    """
    bad = unencodable_characters(text, encoding)
    data = text.encode(encoding, errors="replace")
    return EncodeReport(data=data, unencodable=bad, substituted=bool(bad))


def decode_legacy(data: bytes) -> str:
    """Decode legacy file bytes: cp1252, with undefined bytes as same-valued C1."""
    chars: list[str] = []
    for b in data:
        try:
            chars.append(bytes([b]).decode("cp1252"))
        except UnicodeDecodeError:
            chars.append(chr(b))
    return "".join(chars)


def sanitize_for_display(text: str) -> str:
    """Return a copy safe for terminals: C1 controls become a visible token."""
    out = []
    for ch in text:
        cp = ord(ch)
        if 0x80 <= cp <= 0x9F:
            out.append(f"\\x{cp:02x}")
        else:
            out.append(ch)
    return "".join(out)
