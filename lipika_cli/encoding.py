"""Legacy single-byte encode/decode and terminal display sanitizer."""

from __future__ import annotations

from dataclasses import dataclass

# Characters undefined in cp1252 (bytes 0x81, 0x8D, 0x8F, 0x90, 0x9D); they map
# to the same-valued C1 codepoints on decode.
_UNDEFINED_CP1252 = frozenset("\x81\x8d\x8f\x90\x9d")


@dataclass(frozen=True)
class EncodeReport:
    """Outcome of encoding a legacy string."""

    data: bytes
    replaced: list[str]  # characters substituted with '?'
    warned: bool = False  # True once the caller has been told about `replaced`


def encode_legacy(text: str, encoding: str) -> EncodeReport:
    """Encode text for saving; unencodable characters are reported, not replaced.

    Never substitutes silently: on failure, `replaced` lists the offending
    characters and the caller decides what to do (see §9.3).
    """
    data = text.encode(encoding, errors="strict")
    return EncodeReport(data=data, replaced=[])


def encode_legacy_after_warning(text: str, encoding: str) -> EncodeReport:
    """Second-pass encode after the caller has warned; unencodable -> '?'."""
    data = text.encode(encoding, errors="replace")
    return EncodeReport(data=data, replaced=[], warned=True)


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
