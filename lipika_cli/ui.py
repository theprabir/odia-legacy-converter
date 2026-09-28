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
    """Large gradient heading panel; compact fallback for narrow terminals."""
    if not color_enabled():
        console.print(_arrow())
        console.print(AUTHOR)
        console.print(GITHUB_URL)
        console.print(HINT)
        return

    title = Text(_arrow())
    title.stylize("bold cyan")
    body = Text()
    body.append(title)
    body.append("\n")
    body.append(AUTHOR, style="italic")
    body.append("\n")
    body.append(GITHUB_URL, style=f"link {GITHUB_URL} underline")
    body.append("\n")
    body.append(HINT, style="dim")

    if _console_width() < 60:
        console.print(body)
        return

    # Gradient: per-character colour ramp across the title line.
    gradient = Text()
    colors = [(0, 191, 255), (0, 255, 255), (0, 255, 127), (173, 255, 47)]
    for i, ch in enumerate(_arrow()):
        t = i / max(len(_arrow()) - 1, 1)
        r, g, b = colors[min(int(t * len(colors)), len(colors) - 1)]
        gradient.append(ch, style=f"bold rgb({r},{g},{b})")

    panel = Panel(
        gradient + Text("\n") + AUTHOR + Text("\n") + Text(GITHUB_URL, style=f"link {GITHUB_URL} underline") + Text("\n") + Text(HINT, style="dim"),
        border_style="cyan",
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
