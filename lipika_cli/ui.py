"""Rich rendering: banner, help table, result panels, messages.

One palette, defined here. All user-facing strings route through this module
or `branding.py`.
"""

from __future__ import annotations

import os
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from lipika_cli.branding import AUTHOR, GITHUB_URL, HINT, TITLE, TITLE_ASCII
from lipika_cli.encoding import sanitize_for_display
from lipika_cli.engine import Result
from lipika_cli.modes import MODES, U2A, U2S

console = Console()

# --- 3D-typography headline -----------------------------------------------
# Hand-drawn block letters (figlet-style, 5 rows). '⇄' is drawn as '<->' so
# every glyph stays pure ASCII and survives any terminal encoding.

_LETTERS: dict[str, list[str]] = {
    "A": [" █████╗ ", "██╔══██╗", "███████║", "██╔══██║", "██║  ██║", "╚═╝  ╚═╝"],
    "C": [" ██████╗", "██╔════╝", "██║     ", "██║     ", "╚██████╗", " ╚═════╝"],
    "E": ["███████╗", "██╔════╝", "█████╗  ", "██╔══╝  ", "███████╗", "╚══════╝"],
    "I": ["██╗", "██║", "██║", "██║", "██║", "╚═╝"],
    "K": ["██╗  ██╗", "██║ ██╔╝", "█████╔╝ ", "██╔═██╗ ", "██║  ██╗", "╚═╝  ╚═╝"],
    "L": ["██╗     ", "██║     ", "██║     ", "██║     ", "███████╗", "╚══════╝"],
    "N": ["███╗   ██╗", "████╗  ██║", "██╔██╗ ██║", "██║╚██╗██║", "██║ ╚████║", "╚═╝  ╚═══╝"],
    "O": [" ██████╗ ", "██╔═══██╗", "██║   ██║", "██║   ██║", "╚██████╔╝", " ╚═════╝ "],
    "P": ["██████╗ ", "██╔══██╗", "██████╔╝", "██╔═══╝ ", "██║     ", "╚═╝     "],
    "R": ["██████╗ ", "██╔══██╗", "██████╔╝", "██╔══██╗", "██║  ██║", "╚═╝  ╚═╝"],
    "S": [" ███████╗", "██╔══════╝", "███████╗  ", "╚═════██╗ ", "█████████╗", "╚═════════╝"],
    "T": ["████████╗", "╚══██╔══╝", "   ██║   ", "   ██║   ", "   ██║   ", "   ╚═╝   "],
    "U": ["██╗   ██╗", "██║   ██║", "██║   ██║", "██║   ██║", "╚██████╔╝", " ╚═════╝ "],
    "V": ["██╗   ██╗", "██║   ██║", "██║   ██║", "╚██╗ ██╔╝", " ╚████╔╝ ", "  ╚═══╝  "],
    "W": ["██╗    ██╗", "██║    ██║", "██║ █╗ ██║", "██║███╗██║", "╚███╔███╔╝", " ╚══╝╚══╝ "],
    "/": ["     ██╗/", "    ██╔╝/", "   ██╔╝ /", "  ██╔╝  /", " ██╔╝   /", " ╚═╝    /"],
    "-": ["─────────", "─────────", "─────────", "─────────", "─────────", "─────────"],
    ">": ["██╗", "╚██╗", " ╚██╗", "  ╚██╗", "   ╚██╗", "    ╚═╝"],
    "<": ["██╗", "██╔╝", "██╔╝ ", "██╔╝  ", "██╔╝   ", "╚═╝    "],
    " ": ["   ", "   ", "   ", "   ", "   ", "   "],
}

# Draw the heading as: UNICODE <-> AKRUTI/SREELIPI
_HEADLINE = "UNICODE <-> AKRUTI"

# Missing glyphs collapse to a blank slot so an unexpected char can't crash
# the banner.


def _headline_rows() -> list[str]:
    rows: list[list[str]] = [[""] for _ in range(6)]
    for ch in _HEADLINE:
        glyph = _LETTERS.get(ch.upper(), _LETTERS[" "])
        for i in range(6):
            rows[i].append(glyph[i])
    return ["".join(r).rstrip() for r in rows]


def _gradient_rows_text() -> Text:
    """Six-row block headline with a top-to-bottom colour gradient."""
    rows = _headline_rows()
    # Gradient runs per-row (depth feel) with a hue sweep across the width.
    row_colors = ["#7df9ff", "#00cfff", "#0091ff", "#6a5cff", "#9b5cff", "#c95cff"]
    text = Text()
    for r, row in enumerate(rows):
        text.append(" " + row + "\n", style=f"bold {row_colors[r]}")
    return text


def _shadow_text() -> Text:
    """Unused placeholder retained for future shadow styling."""
    rows = _headline_rows()
    text = Text()
    for row in rows:
        text.append(" " + row + "\n", style="dim #3a0ca3")
    return text


def color_enabled() -> bool:
    """NO_COLOR, non-terminal, or forced no-color disables colour/panels."""
    return (
        not os.environ.get("NO_COLOR")
        and console.is_terminal
        and not console.no_color
    )


def _console_width() -> int:
    return console.size.width


def _arrow() -> str:
    """Use ASCII arrow when the terminal cannot render '⇄'."""
    if color_enabled() and _console_width() >= 60:
        try:
            "⇄".encode(sys.stdout.encoding or "utf-8")
            return TITLE
        except (UnicodeEncodeError, LookupError):
            return TITLE_ASCII
    return TITLE_ASCII


def render_banner() -> None:
    """Large gradient 3D headline panel; compact fallback for narrow/plain."""
    if not color_enabled():
        console.print(_arrow())
        console.print(AUTHOR)
        console.print(GITHUB_URL)
        console.print(HINT)
        return

    if _console_width() < 60:
        body = Text(_arrow(), style="bold cyan")
        body.append("\n")
        body.append(AUTHOR, style="italic")
        body.append("\n")
        body.append(GITHUB_URL, style=f"link {GITHUB_URL} underline")
        body.append("\n")
        body.append(HINT, style="dim")
        console.print(body)
        return

    headline = _gradient_rows_text()
    subtitle = Text()
    subtitle.append(TITLE_ASCII + "\n", style="bold white")
    subtitle.append(AUTHOR + "\n", style="italic")
    subtitle.append(GITHUB_URL + "\n", style=f"link {GITHUB_URL} underline")
    subtitle.append(HINT, style="dim")

    panel = Panel(
        headline + subtitle,
        border_style="bright_cyan",
        padding=(0, 2),
    )
    console.print(panel)


def render_help() -> None:
    """Compact help table per §7."""
    if not color_enabled():
        console.print(
            "Convert\n"
            "  /u2a  Unicode -> Akruti      /a2u  Akruti -> Unicode\n"
            "  /u2s  Unicode -> Sreelipi    /s2u  Sreelipi -> Unicode\n"
            "Output\n"
            "  /fix  toggle glyph fix (Akruti)   /copy   /save [file]\n"
            "Other\n"
            "  /clear   h help   /quit\n"
            "Enter = convert · Ctrl+J = new line"
        )
        return
    table = Table.grid(padding=(0, 2))
    table.add_row("[bold]Convert[/bold]")
    table.add_row("  /u2a  Unicode → Akruti", "/a2u  Akruti → Unicode")
    table.add_row("  /u2s  Unicode → Sreelipi", "/s2u  Sreelipi → Unicode")
    table.add_row("[bold]Output[/bold]")
    table.add_row("  /fix  toggle glyph fix (Akruti)", "/copy   /save [file]")
    table.add_row("[bold]Other[/bold]")
    table.add_row("  /clear   h help   /quit")
    table.add_row("[dim]Enter = convert · Ctrl+J = new line[/dim]")
    console.print(table)


def render_error(message: str) -> None:
    """One clear line with the fix; never a traceback."""
    console.print(f"[red]error:[/red] {message}")


def render_message(message: str) -> None:
    console.print(message)


_LEGACY_NOTICE = (
    "Legacy-encoded text looks garbled in a terminal. Use /save or /copy, "
    "then apply the font."
)


def render_result(result: Result) -> None:
    """Result panel titled with the mode label; footer `N chars → M chars`."""
    is_legacy_output = result.mode.engine_fn in (U2A, U2S)
    display = sanitize_for_display(result.text) if is_legacy_output else result.text

    footer = Text()
    footer.append(f"{result.n_in} chars → {result.n_out} chars", style="dim")

    if not color_enabled():
        console.print(result.text)
        console.print(footer.plain)
        if is_legacy_output:
            console.print(_LEGACY_NOTICE)
        return

    body = Text(display)
    if is_legacy_output:
        body.append("\n")
        body.append(_LEGACY_NOTICE, style="dim")
    body.append("\n")
    body.append(footer)

    panel = Panel(
        body,
        title=result.mode.label,
        border_style="green" if not is_legacy_output else "yellow",
    )
    console.print(panel)


def mode_label_coloured(mode_command: str) -> str:
    """Toolbar fragment for the active mode."""
    mode = MODES[mode_command]
    return f"[cyan]{mode.label}[/cyan]"
