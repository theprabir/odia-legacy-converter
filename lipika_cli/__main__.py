"""Entry point for ``python -m lipika_cli``; handles --version."""

import sys

from lipika_cli import __version__

VERSION_TEXT = f"lipika {__version__}"


def main() -> None:
    """Dispatch: --version prints and exits; full CLI arrives in Phase 4."""
    if "--version" in sys.argv[1:]:
        print(VERSION_TEXT)
        return
    raise SystemExit("lipika: non-interactive mode is not implemented yet (Phase 4).")


if __name__ == "__main__":
    main()
