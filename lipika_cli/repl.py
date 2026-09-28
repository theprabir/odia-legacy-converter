"""Interactive REPL: state, prompt_toolkit loop, key bindings."""

from __future__ import annotations

from dataclasses import dataclass, field

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style

from lipika_cli import commands, ui
from lipika_cli.engine import Result, convert
from lipika_cli.modes import DEFAULT_COMMAND, U2A, Mode, get_mode
from lipika_cli.save import SaveOutcome, save_result, save_result_substituting

try:  # clipboard is optional; degrade gracefully (§3)
    import pyperclip

    _HAS_CLIPBOARD = True
except ImportError:  # pragma: no cover - import guard
    pyperclip = None  # type: ignore[assignment]
    _HAS_CLIPBOARD = False


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

    # ------------------------------------------------------- layout

    def _scrollback_text(self) -> str:
        return "".join(self.state.scrollback)

    def _toolbar_text(self) -> str:
        st = self.state
        fix = "on" if st.fixed else "off"
        return (
            f" {st.mode.label}  ·  fix: {fix}"
            "  ·  Enter convert · Ctrl+J newline · /quit exit"
        )

    def _build_app(self) -> Application:
        kb = self._build_key_bindings()
        scrollback_window = Window(
            FormattedTextControl(self._scrollback_text), always_hide_cursor=True
        )
        input_window = Window(
            content=BufferControl(buffer=self._buffer),
            height=lambda: max(2, self._buffer.document.line_count + 1),
        )
        toolbar = Window(
            FormattedTextControl(self._toolbar_text),
            height=1,
            style="class:toolbar",
            always_hide_cursor=True,
        )
        root = HSplit([scrollback_window, input_window, toolbar])
        return Application(
            layout=Layout(root),
            key_bindings=kb,
            style=Style([("class", "reverse")]),
            full_screen=False,
            mouse_support=False,
        )

    # --------------------------------------------------- key bindings

    def _build_key_bindings(self) -> KeyBindings:
        kb = KeyBindings()

        @kb.add("enter")
        def _submit(event) -> None:  # type: ignore[no-untyped-def]
            text = self._buffer.text
            self._buffer.reset()
            self._handle_submit(text)

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

    # ---------------------------------------------------- handling

    def _append_scrollback(self, rendered: str) -> None:
        self.state.scrollback.append(rendered)

    def _handle_submit(self, raw: str) -> None:
        # A pending /save confirmation eats the next input entirely.
        if self.state.pending_save_path is not None:
            path = self.state.pending_save_path
            self.state.pending_save_path = None
            self._finish_save(raw.strip(), path)
            return

        parsed = commands.parse(raw)

        if isinstance(parsed, commands.Ignore):
            return
        if isinstance(parsed, commands.Quit):
            self._quit_requested = True
            return
        if isinstance(parsed, commands.Help):
            self._append_scrollback(help_text())
            return
        if isinstance(parsed, commands.Unknown):
            self._append_scrollback(
                f"error: unknown command {parsed.name!r} - type h for help\n"
            )
            return

        if isinstance(parsed, commands.Command):
            self._run_command(parsed)
            return

        assert isinstance(parsed, commands.Message)
        try:
            result = convert(self.state.mode, raw.strip(), fixed=self.state.fixed)
        except TypeError as exc:
            self._append_scrollback(f"error: {exc}\n")
            return
        self.state.last_result = result
        self._append_scrollback(result_text(result))

    _quit_requested = False

    # --------------------------------------------------- commands

    def _run_command(self, cmd: commands.Command) -> None:
        if cmd.name in commands.MODE_COMMANDS:
            self.state.mode_command = cmd.name
            self._append_scrollback(f"mode: {self.state.mode.label}\n")
        elif cmd.name == "/clear":
            self.state.scrollback.clear()
            self.state.scrollback.append(capture(ui.render_banner))
        elif cmd.name == "/fix":
            self._toggle_fix()
        elif cmd.name == "/copy":
            self._copy_last()
        elif cmd.name == "/save":
            self._save_last(cmd.arg)
        else:  # pragma: no cover - registry keeps this unreachable
            raise AssertionError(f"unhandled command {cmd.name}")

    def _toggle_fix(self) -> None:
        self.state.fixed = not self.state.fixed
        if self.state.mode.engine_fn != U2A:
            self._append_scrollback(
                "note: glyph fix only affects Unicode → Akruti (/u2a)\n"
            )
        self._append_scrollback(f"fix: {'on' if self.state.fixed else 'off'}\n")

    # ------------------------------------------------------ /save

    def _save_last(self, arg: str | None) -> None:
        result = self.state.last_result
        if result is None:
            self._append_scrollback("error: nothing to save yet - convert first\n")
            return

        outcome = save_result(result, arg)
        if outcome.ok:
            self._append_scrollback(self._save_ok_message(outcome))
            return

        # §9.3: report count + characters, then offer '?'-substitution.
        assert outcome.unencodable is not None and outcome.encoding is not None
        chars = ", ".join(f"{ch!r}" for ch in outcome.unencodable)
        self._append_scrollback(
            f"warning: {len(outcome.unencodable)} character(s) cannot be "
            f"encoded as {outcome.encoding}: {chars}\n"
        )
        self._append_scrollback(
            "warning: file NOT written. Reply y to replace them with '?', "
            "or anything else to cancel\n"
        )
        self.state.pending_save_path = str(outcome.path) if outcome.path else None

    def _finish_save(self, answer: str, path: str) -> None:
        """Complete a pending /save after the user answered the warning."""
        result = self.state.last_result
        assert result is not None  # pending path implies a result exists
        if answer.lower() not in ("y", "yes"):
            self._append_scrollback("save cancelled - nothing written\n")
            return
        outcome = save_result_substituting(result, path)
        self._append_scrollback(self._save_ok_message(outcome))

    def _save_ok_message(self, outcome: SaveOutcome) -> str:
        assert outcome.path is not None and outcome.encoding is not None
        msg = f"saved: {outcome.path} ({outcome.encoding})"
        if outcome.unencodable:
            chars = ", ".join(f"{ch!r}" for ch in outcome.unencodable)
            msg += f" - {len(outcome.unencodable)} character(s) written as '?': {chars}"
        return msg + "\n"

    # ------------------------------------------------------ /copy

    def _copy_last(self) -> None:
        result = self.state.last_result
        if result is None:
            self._append_scrollback("error: nothing to copy yet\n")
            return
        if not _HAS_CLIPBOARD:
            self._append_scrollback(
                "error: clipboard unavailable (install pyperclip backend)\n"
            )
            return
        try:
            pyperclip.copy(result.text)  # type: ignore[union-attr]
        except (OSError, ValueError, RuntimeError) as exc:
            self._append_scrollback(f"error: clipboard copy failed: {exc}\n")
            return
        msg = "copied"
        if result.fixed and result.mode.engine_fn == U2A:
            msg += (
                " - warning: fixed-mode C1 glyphs are often stripped by the "
                "clipboard; /save is lossless"
            )
        self._append_scrollback(msg + "\n")

    # ------------------------------------------------------- run

    def run(self) -> None:
        self._quit_requested = False
        self.state.scrollback.append(capture(ui.render_banner))
        self.app = self._build_app()
        self.app.run()


# ------------------------------------------------------- rendering glue
# Pure helpers kept outside Repl so tests can assert on strings.


def capture(render_fn) -> str:  # type: ignore[no-untyped-def]
    """Render a ui function to a plain-text string for the scrollback."""
    from rich.console import Console

    buf = Console(record=True, width=100, force_terminal=False, no_color=True)
    original = ui.console
    ui.console = buf  # type: ignore[assignment]
    try:
        render_fn()
    finally:
        ui.console = original
    return buf.export_text()


def result_text(result: Result) -> str:
    """Plain-text rendering of a result (legacy output sanitized)."""
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
