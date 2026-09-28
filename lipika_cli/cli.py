"""Non-interactive CLI: subcommands mirroring the four modes (Phase 4)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lipika_cli import __version__
from lipika_cli.encoding import decode_legacy, unencodable_characters
from lipika_cli.engine import convert
from lipika_cli.modes import MODES

VERSION_TEXT = f"lipika {__version__}"

DEBUG_USAGE = "re-run with --debug to see the full traceback"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lipika",
        description="Odia Unicode, Akruti and Sreelipi text converter.",
    )
    parser.add_argument("--version", action="store_true", help=VERSION_TEXT)
    parser.add_argument(
        "--debug",
        action="store_true",
        help="show full tracebacks instead of one-line errors",
    )
    sub = parser.add_subparsers(dest="mode_command", metavar="MODE")

    for name, mode in MODES.items():
        sp = sub.add_parser(
            name.lstrip("/"),
            help=mode.label.replace("→", "->"),
        )
        sp.add_argument("text", nargs="?", help="text to convert")
        sp.add_argument(
            "-f", "--file", help="read input from a file (legacy files decode as cp1252)"
        )
        sp.add_argument(
            "-o", "--out", help="write the result to a file instead of stdout"
        )
        sp.add_argument(
            "--fixed",
            action="store_true",
            help="apply the Windows glyph fix (only meaningful for u2a)",
        )
        sp.add_argument(
            "--encoding",
            help="override the output encoding for -o (default per mode)",
        )

    return parser


def _read_input(args: argparse.Namespace) -> str:
    """Input precedence: -f file > text argument > stdin pipe.

    Files are decoded smartly: try UTF-8 first (modern Odia text), fall back
    to legacy cp1252-with-C1-fallback (Akruti/Sreelipi saved files). This
    matches user expectation: `-f` works for both Unicode and legacy files.
    """
    if args.file:
        data = Path(args.file).read_bytes()
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return decode_legacy(data)
    if args.text is not None:
        return args.text
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit(
        "lipika: no input - pass text, -f FILE, or pipe stdin "
        "(example: lipika u2a \"ନମସ୍କାର\")"
    )


def _write_output(text: str, args: argparse.Namespace) -> int:
    """Write to -o file (mode encoding) or stdout (UTF-8)."""
    if not args.out:
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.flush()
        return 0

    mode = MODES[f"/{args.mode_command}"]
    encoding = args.encoding or mode.output_encoding(args.fixed)
    bad = unencodable_characters(text, encoding)
    if bad:
        chars = ", ".join(repr(ch) for ch in bad)
        print(
            f"warning: {len(bad)} character(s) not encodable as {encoding} "
            f"written as '?': {chars}",
            file=sys.stderr,
        )
        data = text.encode(encoding, errors="replace")
    else:
        data = text.encode(encoding, errors="strict")
    Path(args.out).write_bytes(data)
    return 0


def run_conversion(args: argparse.Namespace) -> int:
    """Execute one non-interactive conversion; returns process exit code."""
    mode = MODES[f"/{args.mode_command}"]
    text = _read_input(args)
    if not text:
        print("warning: empty input - nothing to convert", file=sys.stderr)
        return 1

    try:
        result = convert(mode, text, fixed=args.fixed)
    except TypeError as exc:
        if args.debug:
            raise
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.fixed and mode.engine_fn != "convert_text":
        print(
            "note: --fixed only applies to 'u2a' - ignored for this mode",
            file=sys.stderr,
        )

    return _write_output(result.text, args)


def main(argv: list[str] | None = None) -> int:
    """Console-script entry: dispatch to non-interactive mode or the REPL."""
    argv = list(sys.argv[1:] if argv is None else argv)

    # No arguments at all -> interactive shell.
    if not argv:
        from lipika_cli.repl import Repl

        Repl().run()
        return 0

    parser = build_parser()
    if "--version" in argv:
        print(VERSION_TEXT)
        return 0
    try:
        args = parser.parse_args(argv)
    except UnicodeEncodeError:
        # Legacy Windows console (cp1252): argparse help contains non-ASCII.
        parser.exit(2, "lipika: console cannot display help text; see README.md\n")

    if args.mode_command is None:
        parser.print_help()
        return 0

    try:
        return run_conversion(args)
    except (OSError, UnicodeError) as exc:
        if args.debug:
            raise
        print(f"error: {exc}", file=sys.stderr)
        print(DEBUG_USAGE, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
