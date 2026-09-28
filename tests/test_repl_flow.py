"""REPL flow tests: state transitions via _handle_submit, no real terminal.

Interactive behaviour (rendering, key bindings, paste) is on the phase's
manual checklist; AGENTS.md says to test parsing/state logic as pure logic.
"""

import pytest

from lipika_cli.engine import Result
from lipika_cli.modes import get_mode
from lipika_cli.repl import Repl, help_text, result_text


@pytest.fixture()
def repl():
    r = Repl()
    r.state.scrollback.clear()  # drop the banner captured in __init__
    return r


class TestModeSwitching:
    def test_default_mode_is_u2a(self, repl):
        assert repl.state.mode_command == "/u2a"

    def test_switch_modes_sticky(self, repl):
        for name in ("/a2u", "/s2u", "/u2s"):
            repl._handle_submit(name)
            assert repl.state.mode_command == name

    def test_unknown_command_adds_error(self, repl):
        repl._handle_submit("/nope")
        assert any("unknown command" in line for line in repl.state.scrollback)

    def test_help_adds_help_text(self, repl):
        repl._handle_submit("h")
        assert help_text() in "".join(repl.state.scrollback)


class TestConversion:
    def test_message_converts_and_stores_last_result(self, repl):
        repl._handle_submit("ନମସ୍କାର")
        result = repl.state.last_result
        assert isinstance(result, Result)
        assert result.mode == get_mode("/u2a")
        assert result.text  # engine produced legacy bytes

    def test_result_text_contains_footer(self, repl):
        repl._handle_submit("ନମସ୍କାର")
        out = "".join(repl.state.scrollback)
        assert "chars →" in out
        assert "Legacy-encoded text looks garbled" in out

    def test_unicode_output_has_no_legacy_notice(self, repl):
        repl._handle_submit("/a2u")
        repl.state.scrollback.clear()
        # VERIFIED: 'IWÿò@û' is the a2u legacy form of 'ଓଡ଼ିଆ' (phase 1 probe).
        repl._handle_submit("IWÿò@û")
        out = "".join(repl.state.scrollback)
        assert "Legacy-encoded" not in out
        assert "ଓଡ଼ିଆ" in out

    def test_empty_submit_ignored(self, repl):
        repl._handle_submit("   ")
        assert repl.state.last_result is None
        assert repl.state.scrollback == []

    def test_type_error_surfaces_as_error_line(self, repl):
        # Adapter propagates TypeError; the REPL must show one clear line.
        import lipika_cli.repl as repl_mod

        def boom(*a, **k):
            raise TypeError("boom")

        original = repl_mod.convert
        repl_mod.convert = boom
        try:
            repl._handle_submit("x")
        finally:
            repl_mod.convert = original
        assert any("error:" in line for line in repl.state.scrollback)


class TestFixToggle:
    def test_toggle_roundtrip(self, repl):
        repl._handle_submit("/fix")
        assert repl.state.fixed is True
        repl._handle_submit("/fix")
        assert repl.state.fixed is False

    def test_fix_warns_outside_u2a(self, repl):
        repl._handle_submit("/a2u")
        repl.state.scrollback.clear()
        repl._handle_submit("/fix")
        out = "".join(repl.state.scrollback)
        assert "only affects Unicode → Akruti" in out


class TestCopyCommand:
    def test_copy_with_no_result_errors(self, repl):
        repl._handle_submit("/copy")
        assert any("nothing to copy" in line for line in repl.state.scrollback)


class TestClearCommand:
    def test_clear_empties_scrollback_and_redraws_banner(self, repl):
        repl._handle_submit("ନମସ୍କାର")
        repl._handle_submit("/clear")
        assert len(repl.state.scrollback) == 1
        assert "Converter" in repl.state.scrollback[0]


class TestQuitCommand:
    def test_quit_marks_exit(self, repl):
        repl._handle_submit("/quit")
        assert repl._quit_requested is True


class TestResultTextPure:
    def test_legacy_result_sanitized(self):
        from lipika_cli.engine import convert

        result = convert(get_mode("/u2a"), "ତ୍ତ", fixed=True)
        text = result_text(result)
        assert "\\x8f" in text  # sanitizer token, not raw C1

    def test_unicode_result_not_sanitized(self):
        from lipika_cli.engine import convert

        result = convert(get_mode("/a2u"), "IWÿò@û")
        text = result_text(result)
        assert "ନମସ୍କାର" not in text  # a2u of unrelated legacy text
