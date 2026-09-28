"""ONLY importer of `converter_engine`; routes a mode to the engine function."""

from __future__ import annotations

from dataclasses import dataclass

import converter_engine
from lipika_cli.modes import U2A, Mode


@dataclass(frozen=True)
class Result:
    """A conversion outcome; `text` is the real (unsanitized) engine string."""

    text: str
    mode: Mode
    fixed: bool
    n_in: int
    n_out: int


def convert(mode: Mode, text: str, fixed: bool = False) -> Result:
    """Run `text` through the engine function for `mode`.

    Raises TypeError for non-str input (propagated from the engine).
    """
    fn = getattr(converter_engine, mode.engine_fn)
    if mode.engine_fn == U2A:
        out = fn(text, fix_special_chars=fixed)
    else:
        out = fn(text)
    return Result(text=out, mode=mode, fixed=fixed, n_in=len(text), n_out=len(out))
