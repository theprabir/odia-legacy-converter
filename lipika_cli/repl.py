"""Interactive REPL: state, prompt_toolkit loop, key bindings.

Scrollback entries are ANSI strings produced by a dedicated rich Console
(so panels, colours and emoji survive into scrollback exactly as printed).
Submitted input is echoed into the scrollback before the result, so the
transcript shows question and answer like a chat.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style

from lipika_cli import commands
from lipika_cli.engine import Result, convert
from lipika_cli.modes import DEFAULT_COMMAND, U2A, Mode, get_mode
from lipika_cli.save import SaveOutcome, save_result, save_result_substituting

try:  # clipboard is optional; degrade gracefully (§3)
    import pyperclip

    _HAS_CLIPBOARD = True
except ImportError:  # pragma: no cover - import guard
    pyperclip = None  # type: ignore[assignment]
    _HAS_CLIPBOARD = False


def _make_ansi_console():
    """A rich Console that emits ANSI with the real terminal width."""
    from rich.console import Console

    return Console(force_terminal=True, no_color=bool(os.environ.get("NO_COLOR")))


@dataclass
class ReplState:
    """All mutable REPL state; no module-level globals."""

    mode_command: str = DEFAULT_COMMAND
    fixed: bool = False
    last_result: Result | None = None
    pending_save_path: str | None = None  # set after an unencodable /save
    scrollback: list[str] = field(default_factory=list)

    @property
    def mode(self) -> Mode:
        mode = get_mode(self.mode_command)
        assert mode is not None  # registry guarantees known commands
        return mode


class Repl:
    """Chat-style REPL around the converter engine.

    Submit handling (`_handle_submit`) is terminal-independent so tests can
    drive it directly; the prompt_toolkit Application is built lazily in
    `run()` because constructing it needs a real console.
    """

    def __init__(self) -> None:
        self.state = ReplState()
        self._buffer = Buffer(multiline=True)
        self._ansi = _make_ansi_console()

    # ------------------------------------------------------- rendering

    def _capture(self, render_fn) -> str:  # type: ignore[no-untyped-def]
        """Render a ui function to an ANSI string for the scrollback."""
        import io as _io

        from rich.console import Console

        buf = Console(
            file=_io.StringIO(),
            force_terminal=True,
            width=min(self._ansi.width, 120),
            no_color=self._ansi.no_color,
        )
        original = self._swap_console(buf)
        try:
            render_fn()
        finally:
            self._swap_console(original)
        out = buf.file.getvalue()  # type: ignore[union-attr]
        return out.rstrip("\n") + "\n"

    def _swap_console(self, new_console):  # type: ignore[no-untyped-def]
        import lipika_cli.ui as ui_mod

        original = ui_mod.console
        ui_mod.console = new_console  # type: ignore[assignment]
        return original

    def _echo_input(self, raw: str) -> None:
        """Show what the user submitted, like a chat transcript."""
        lines = raw.rstrip("\n").split("\n") or [""]
        first = f"\x1b[96m❯\x1b[0m \x1b[97m{lines[0]}\x1b[0m"
        rest = "".join(f"\n  \x1b[97m{ln}\x1b[0m" for ln in lines[1:])
        self._append(f"{first}{rest}\n")

    def _append(self, ansi_text: str) -> None:
        self.state.scrollback.append(ansi_text)

    # ------------------------------------------------------- layout

    def _scrollback_text(self) -> str:

        return "".join(self.state.scrollback)  # type: ignore[return-value]

    def _toolbar_text(self) -> str:
        from prompt_toolkit.formatted_text import HTML

        st = self.state
        fix = "on" if st.fixed else "off"
        return HTML(
            f" <style bg='ansibrightblack'>"
            f" <ansicyan>{st.mode.label}</ansicyan>"
            f"  ·  fix: {fix}"
            f"  ·  Enter convert · Ctrl+J newline · /quit exit </style>"
        )

    def _build_app(self) -> Application:
        kb = self._build_key_bindings()

        def _scrollback():
            from prompt_toolkit.formatted_text import ANSI

            return ANSI("".join(self.state.scrollback))

        scrollback_window = Window(
            content=FormattedTextControl(_scrollback),
            wrap_lines=True,
            always_hide_cursor=True,
            # Pin the view to the bottom so new output stays visible.
            get_vertical_scroll=lambda window: max(
                0,
                (window.content.line_count or 0)
                - window.render_info.window_height,
            ),
        )
        input_window = Window(
            content=self._buffer_control(),
            height=lambda: max(2, self._buffer.document.line_count + 1),
            dont_extend_height=True,
        )
        toolbar = Window(
            FormattedTextControl(self._toolbar_text),
            height=1,
            dont_extend_height=True,
            always_hide_cursor=True,
        )
        root = HSplit([scrollback_window, input_window, toolbar])
        self._scrollback_window = scrollback_window
        return Application(
            layout=Layout(root, focused_element=input_window),
            key_bindings=kb,
            style=Style([("class", "reverse")]),
            full_screen=False,
            mouse_support=False,
        )

    def _buffer_control(self):  # type: ignore[no-untyped-def]
        from prompt_toolkit.layout.controls import BufferControl
        from prompt_toolkit.layout.processors import BeforeInput

        return BufferControl(
            buffer=self._buffer,
            input_processors=[
                BeforeInput("❯ ", "ansibrightcyan"),
            ],
        )

    # --------------------------------------------------- key bindings

    def _build_key_bindings(self) -> KeyBindings:
        kb = KeyBindings()

        @kb.add("enter")
        def _submit(event) -> None:  # type: ignore[no-untyped-def]
            text = self._buffer.text
            self._buffer.reset()
            self._handle_submit(text)
            self._scroll_to_bottom()
            if self._quit_requested:
                event.app.exit()

        @kb.add("c-j")
        def _newline(event) -> None:  # type: ignore[no-untyped-def]
            # Ctrl+J inserts a newline (Enter must not be ambiguous).
            self._buffer.insert_text("\n")

        @kb.add("c-c")
        def _clear_input(event) -> None:  # type: ignore[no-untyped-def]
            self._buffer.reset()

        @kb.add("c-d")
        def _exit(event) -> None:  # type: ignore[no-untyped-def]
            event.app.exit()

        return kb

    def _scroll_to_bottom(self) -> None:
        """Invalidate so the get_vertical_scroll pin takes effect immediately."""
        app = getattr(self, "app", None)
        if app is not None and app.render_counter is not None:
            app.invalidate()

    # ---------------------------------------------------- handling

    def _handle_submit(self, raw: str) -> None:
        # A pending /save confirmation eats the next input entirely.
        if self.state.pending_save_path is not None:
            path = self.state.pending_save_path
            self.state.pending_save_path = None
            self._echo_input(raw)
            self._finish_save(raw.strip(), path)
            return

        parsed = commands.parse(raw)

        if isinstance(parsed, commands.Ignore):
            return

        self._echo_input(raw)

        if isinstance(parsed, commands.Quit):
            self._quit_requested = True
            return
        if isinstance(parsed, commands.Help):
            self._append(self._capture(render_help_for_scrollback))
            return
        if isinstance(parsed, commands.Unknown):
            self._append(
                f"\x1b[31merror:\x1b[0m unknown command {parsed.name!r}"
                " - type h for help\n"
            )
            return
        if isinstance(parsed, commands.Command) and parsed.name in (
            "/quit",
            "/exit",
        ):
            self._quit_requested = True
            return

        if isinstance(parsed, commands.Command):
            self._run_command(parsed)
            return

        assert isinstance(parsed, commands.Message)
        try:
            result = convert(self.state.mode, raw.strip(), fixed=self.state.fixed)
        except TypeError as exc:
            self._append(f"\x1b[31merror:\x1b[0m {exc}\n")
            return
        self.state.last_result = result
        self._append(self._capture(lambda: render_result_ansi(result)))

    _quit_requested = False

    # --------------------------------------------------- commands

    def _run_command(self, cmd: commands.Command) -> None:
        if cmd.name in commands.MODE_COMMANDS:
            self.state.mode_command = cmd.name
            self._append(
                f"\x1b[36m➜ mode:\x1b[0m {self.state.mode.label}\n"
            )
        elif cmd.name == "/clear":
            self.state.scrollback.clear()
            self._append(self._capture(banner_fn()))
            self._scroll_to_bottom()
        elif cmd.name == "/fix":
            self._toggle_fix()
        elif cmd.name == "/copy":
            self._copy_last()
        elif cmd.name == "/save":
            self._save_last(cmd.arg)
        elif cmd.name in commands.QUIT_COMMANDS:
            self._quit_requested = True
        else:  # pragma: no cover - registry keeps this unreachable
            raise AssertionError(f"unhandled command {cmd.name}")

    def _toggle_fix(self) -> None:
        self.state.fixed = not self.state.fixed
        if self.state.mode.engine_fn != U2A:
            self._append(
                "\x1b[33mnote:\x1b[0m glyph fix only affects Unicode → Akruti (/u2a)\n"
            )
        state_txt = "\x1b[32mon\x1b[0m" if self.state.fixed else "\x1b[2moff\x1b[0m"
        self._append(f"fix: {state_txt}\n")

    # ------------------------------------------------------ /save

    def _save_last(self, arg: str | None) -> None:
        result = self.state.last_result
        if result is None:
            self._append(
                "\x1b[31merror:\x1b[0m nothing to save yet - convert first\n"
            )
            return

        outcome = save_result(result, arg)
        if outcome.ok:
            self._append(self._save_ok_message(outcome))
            return

        # §9.3: report count + characters, then offer '?'-substitution.
        assert outcome.unencodable is not None and outcome.encoding is not None
        chars = ", ".join(f"{ch!r}" for ch in outcome.unencodable)
        self._append(
            f"\x1b[33mwarning:\x1b[0m {len(outcome.unencodable)} character(s) cannot be "
            f"encoded as {outcome.encoding}: {chars}\n"
        )
        self._append(
            "\x1b[33mwarning:\x1b[0m file NOT written. Reply y to replace them with "
            "'?', or anything else to cancel\n"
        )
        self.state.pending_save_path = str(outcome.path) if outcome.path else None

    def _finish_save(self, answer: str, path: str) -> None:
        """Complete a pending /save after the user answered the warning."""
        result = self.state.last_result
        assert result is not None  # pending path implies a result exists
        if answer.lower() not in ("y", "yes"):
            self._append("save cancelled - nothing written\n")
            return
        outcome = save_result_substituting(result, path)
        self._append(self._save_ok_message(outcome))

    def _save_ok_message(self, outcome: SaveOutcome) -> str:
        assert outcome.path is not None and outcome.encoding is not None
        msg = (
            f"\x1b[32m✔ saved:\x1b[0m {outcome.path} ({outcome.encoding})"
        )
        if outcome.unencodable:
            chars = ", ".join(f"{ch!r}" for ch in outcome.unencodable)
            msg += (
                f" - {len(outcome.unencodable)} character(s) written as '?': {chars}"
            )
        return msg + "\n"

    # ------------------------------------------------------ /copy

    def _copy_last(self) -> None:
        result = self.state.last_result
        if result is None:
            self._append(
                "\x1b[31merror:\x1b[0m nothing to copy yet - convert first\n"
            )
            return
        if not _HAS_CLIPBOARD:
            self._append(
                "\x1b[31merror:\x1b[0m clipboard unavailable"
                " (install pyperclip backend)\n"
            )
            return
        try:
            pyperclip.copy(result.text)  # type: ignore[union-attr]
        except (OSError, ValueError, RuntimeError) as exc:
            self._append(f"\x1b[31merror:\x1b[0m clipboard copy failed: {exc}\n")
            return
        mode_name = result.mode.label
        msg = f"\x1b[32m✔ copied\x1b[0m ({mode_name}: {result.n_out} chars)"
        if result.fixed and result.mode.engine_fn == U2A:
            msg += (
                " - \x1b[33mwarning:\x1b[0m fixed-mode C1 glyphs are often stripped "
                "by the clipboard; /save is lossless"
            )
        self._append(msg + "\n")

    # ------------------------------------------------------- run

    def run(self) -> None:
        self._quit_requested = False
        self._append(self._capture(banner_fn()))
        self.app = self._build_app()
        self.app.run()


# ------------------------------------------------------- render helpers
# Small bridges so repl can render ui content through its ANSI console.


def banner_fn():  # type: ignore[no-untyped-def]
    from lipika_cli import ui

    return ui.render_banner


def render_help_for_scrollback() -> None:
    from lipika_cli import ui

    ui.render_help()


def render_result_ansi(result: Result) -> None:
    from lipika_cli import ui

    ui.render_result(result)


def result_text(result: Result) -> str:
    """Plain-text rendering of a result (legacy output sanitized) - tests."""
    from lipika_cli.encoding import sanitize_for_display
    from lipika_cli.modes import U2A, U2S

    legacy = result.mode.engine_fn in (U2A, U2S)
    body = sanitize_for_display(result.text) if legacy else result.text
    notice = (
        "\nLegacy-encoded text looks garbled in a terminal. "
        "Use /save or /copy, then apply the font."
        if legacy
        else ""
    )
    return (
        f"┌─ {result.mode.label} ─\n"
        f"{body}\n"
        f"└ {result.n_in} chars → {result.n_out} chars{notice}\n"
    )


def help_text() -> str:
    return (
        "Convert\n"
        "  /u2a  Unicode → Akruti        /a2u  Akruti → Unicode\n"
        "  /u2s  Unicode → Sreelipi      /s2u  Sreelipi → Unicode\n"
        "Output\n"
        "  /fix  toggle glyph fix (Akruti)   /copy   /save [file]\n"
        "Other\n"
        "  /clear   h help   /quit\n"
        "Enter = convert · Ctrl+J = new line\n"
    )
