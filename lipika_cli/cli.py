"""CLI entry point; non-interactive subcommands arrive in Phase 4."""

from __future__ import annotations

import sys

from lipika_cli import __version__

VERSION_TEXT = f"lipika {__version__}"


def main() -> None:
    """Console-script dispatch: --version prints; otherwise run the REPL."""
    if "--version" in sys.argv[1:]:
        print(VERSION_TEXT)
        return
    from lipika_cli.repl import Repl

    Repl().run()
