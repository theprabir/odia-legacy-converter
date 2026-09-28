"""Output handling: /save and /copy support logic (pure, no terminal I/O)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lipika_cli.encoding import (
    EncodeReport,
    encode_legacy_strict,
    unencodable_characters,
)
from lipika_cli.engine import Result
from lipika_cli.modes import U2A, Mode


@dataclass(frozen=True)
class SaveOutcome:
    """Result of a /save attempt; `ok` False means nothing was written."""

    ok: bool
    path: Path | None = None
    encoding: str | None = None
    unencodable: list[str] | None = None  # distinct chars written as '?'
    error: str | None = None


def default_save_name(mode: Mode, fixed: bool) -> str:
    """`converted-<mode>.txt` default name per §11 Phase 3."""
    stem = mode.command.lstrip("/")
    if fixed and mode.engine_fn == U2A:
        stem += "-fixed"
    return f"converted-{stem}.txt"


def save_result(result: Result, path: str | None) -> SaveOutcome:
    """Write `result.text` to `path` (or the default name) in the mode's encoding.

    Strict first: if any character is unencodable, nothing is written and the
    outcome lists them so the caller can warn and confirm '?'-substitution
    (§9.3). `fixed` u2a output goes out as latin-1 per §6/§9.2.
    """
    encoding = result.mode.output_encoding(result.fixed)
    target = Path(path) if path else Path(default_save_name(result.mode, result.fixed))

    text = result.text
    bad = unencodable_characters(text, encoding)
    if bad:
        return SaveOutcome(
            ok=False,
            path=target,
            encoding=encoding,
            unencodable=bad,
        )

    data = text.encode(encoding, errors="strict")
    target.write_bytes(data)
    return SaveOutcome(ok=True, path=target, encoding=encoding)


def save_result_substituting(result: Result, path: str | None) -> SaveOutcome:
    """Second-pass save after the caller has warned; unencodable -> '?'."""
    encoding = result.mode.output_encoding(result.fixed)
    target = Path(path) if path else Path(default_save_name(result.mode, result.fixed))
    data = result.text.encode(encoding, errors="replace")
    target.write_bytes(data)
    bad = unencodable_characters(result.text, encoding)
    return SaveOutcome(ok=True, path=target, encoding=encoding, unencodable=bad)


def strict_report(text: str, encoding: str) -> EncodeReport:
    """Strict encode, for tests and callers that need the bytes directly."""
    return encode_legacy_strict(text, encoding)
