"""Mode registry: slash command, labels, engine function name, output encodings."""

from __future__ import annotations

from dataclasses import dataclass

# Engine function names live as strings so `engine.py` stays the only importer
# of `converter_engine` (they are resolved there).
A2U = "convert_akruti_to_unicode"
S2U = "convert_sreelipi_to_unicode"
U2A = "convert_text"
U2S = "convert_text_sreelipi"


@dataclass(frozen=True)
class Mode:
    """One conversion mode: its slash command, display label and encodings."""

    command: str
    label: str
    engine_fn: str
    encoding_original: str
    encoding_fixed: str | None = None

    def output_encoding(self, fixed: bool) -> str:
        """Encoding for saving/copying output of this mode."""
        if fixed and self.encoding_fixed is not None:
            return self.encoding_fixed
        return self.encoding_original


MODES: dict[str, Mode] = {
    m.command: m
    for m in (
        Mode("/u2a", "Unicode → Akruti", U2A, "cp1252", "latin-1"),
        Mode("/a2u", "Akruti → Unicode", A2U, "utf-8"),
        Mode("/u2s", "Unicode → Sreelipi", U2S, "cp1252"),
        Mode("/s2u", "Sreelipi → Unicode", S2U, "utf-8"),
    )
}

DEFAULT_COMMAND = "/u2a"


def get_mode(command: str) -> Mode | None:
    """Return the mode for a slash command, or None."""
    return MODES.get(command)
