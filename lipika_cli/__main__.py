"""Entry point for ``python -m lipika_cli``; handles --version and the REPL."""

import sys

from lipika_cli import __version__

VERSION_TEXT = f"lipika {__version__}"


def main() -> None:
    """Dispatch: --version prints and exits; otherwise run the REPL."""
    if "--version" in sys.argv[1:]:
        print(VERSION_TEXT)
        return
    from lipika_cli.repl import Repl

    Repl().run()


if __name__ == "__main__":
    main()
