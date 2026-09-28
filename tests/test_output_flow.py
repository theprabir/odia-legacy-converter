"""REPL output-flow tests: /save warnings + confirm, /copy, friendly errors."""

import pytest

from lipika_cli.repl import Repl


@pytest.fixture()
def repl():
    r = Repl()
    r.state.scrollback.clear()
    return r


def _out(repl) -> str:
    return "".join(repl.state.scrollback)


class TestSaveCommand:
    def test_no_result_errors(self, repl):
        repl._handle_submit("/save")
        assert "nothing to save" in _out(repl)

    def test_save_default_name(self, repl, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        repl._handle_submit("ନମସ୍କାର")
        repl._handle_submit("/save")
        assert "saved: converted-u2a.txt (cp1252)" in _out(repl)
        assert (tmp_path / "converted-u2a.txt").exists()

    def test_save_explicit_path(self, repl, tmp_path):
        target = tmp_path / "explicit.txt"
        repl._handle_submit("ନମସ୍କାର")
        repl._handle_submit(f"/save {target}")
        assert f"saved: {target}" in _out(repl)
        assert target.exists()

    def test_fixed_save_uses_latin1(self, repl, tmp_path):
        target = tmp_path / "fixed.txt"
        repl._handle_submit("/fix")
        repl._handle_submit("ସତ୍ତର")
        repl._handle_submit(f"/save {target}")
        assert "latin-1" in _out(repl)
        assert b"\x8f" in target.read_bytes()

    def test_unencodable_warns_then_y_writes(self, repl, tmp_path, monkeypatch):
        # cp1252 cannot carry the C1 codepoints; only reachable by forcing
        # the encoding, so drive save_result via a fake a2u-mode result.
        monkeypatch.chdir(tmp_path)
        from lipika_cli.engine import Result
        from lipika_cli.modes import get_mode

        repl._handle_submit("/fix")
        repl._handle_submit("ସତ୍ତର")
        # rewrite last_result to pretend it must be saved as cp1252
        real = repl.state.last_result
        assert real is not None
        repl.state.last_result = Result(
            text=real.text, mode=get_mode("/a2u"), fixed=True,
            n_in=real.n_in, n_out=real.n_out,
        )
        # a2u's encoding is utf-8 and C1 is encodable there, so instead build
        # the unencodable case directly: fixed C1 text saved via cp1252
        repl.state.last_result = Result(
            text=real.text, mode=get_mode("/u2a"), fixed=False,
            n_in=real.n_in, n_out=real.n_out,
        )
        # u2a + fixed=False means cp1252 without C1 -> would succeed; to hit
        # the warning path we need C1 with cp1252: set fixed True (latin-1 OK)
        # is NOT unencodable, so emulate the C1-in-cp1252 case via mode swap:
        from lipika_cli.modes import Mode

        cp1252_mode = Mode("/u2a", "Unicode → Akruti", "convert_text", "cp1252")
        fixed_result = Result(
            text="\x8f\x81", mode=cp1252_mode, fixed=True, n_in=2, n_out=2,
        )
        repl.state.last_result = fixed_result
        repl._handle_submit("/save")
        out = _out(repl)
        assert "cannot be encoded as cp1252" in out
        assert "file NOT written" in out
        # confirm with y
        repl._handle_submit("y")
        out = _out(repl)
        assert "written as '?'" in out
        assert (tmp_path / "converted-u2a-fixed.txt").read_bytes() == b"??"

    def test_unencodable_warns_then_other_cancels(self, repl, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from lipika_cli.engine import Result
        from lipika_cli.modes import Mode

        cp1252_mode = Mode("/u2a", "Unicode → Akruti", "convert_text", "cp1252")
        repl.state.last_result = Result(
            text="\x8f", mode=cp1252_mode, fixed=True, n_in=1, n_out=1,
        )
        repl._handle_submit("/save")
        repl._handle_submit("n")
        assert "save cancelled" in _out(repl)
        assert not (tmp_path / "converted-u2a-fixed.txt").exists()

    def test_pending_confirmation_eats_next_input(self, repl, tmp_path):
        # While a save confirmation is pending, a normal message must NOT
        # convert anything - the next submit answers the pending question.
        from lipika_cli.engine import Result
        from lipika_cli.modes import Mode

        cp1252_mode = Mode("/u2a", "Unicode → Akruti", "convert_text", "cp1252")
        repl.state.last_result = Result(
            text="\x8f", mode=cp1252_mode, fixed=True, n_in=1, n_out=1,
        )
        repl._handle_submit("/save")
        repl.state.scrollback.clear()
        repl._handle_submit("y")  # treated as the answer, not a message
        out = _out(repl)
        assert "saved" in out  # save completed, not a new conversion
        assert "chars →" not in out  # no conversion result was produced
        assert repl.state.pending_save_path is None


class TestCopyCommand:
    def test_no_result_errors(self, repl):
        repl._handle_submit("/copy")
        assert "nothing to copy" in _out(repl)

    def test_fixed_copy_warns_about_c1(self, repl, monkeypatch):
        import lipika_cli.repl as repl_mod

        monkeypatch.setattr(repl_mod, "_HAS_CLIPBOARD", True)
        monkeypatch.setattr(repl_mod, "pyperclip", _FakeClipboard())
        repl._handle_submit("/fix")
        repl._handle_submit("ସତ୍ତର")
        repl._handle_submit("/copy")
        assert "warning" in _out(repl)
        assert "/save is lossless" in _out(repl)

    def test_plain_copy_has_no_warning(self, repl, monkeypatch):
        import lipika_cli.repl as repl_mod

        monkeypatch.setattr(repl_mod, "_HAS_CLIPBOARD", True)
        monkeypatch.setattr(repl_mod, "pyperclip", _FakeClipboard())
        repl._handle_submit("ନମସ୍କାର")
        repl._handle_submit("/copy")
        assert "copied" in _out(repl)
        assert "warning" not in _out(repl)


class _FakeClipboard:
    def copy(self, text: str) -> None:
        self.text = text


class TestFriendlyErrors:
    def test_engine_type_error_one_line(self, repl, monkeypatch):
        import lipika_cli.repl as repl_mod

        def boom(*a, **k):
            raise TypeError("boom")

        monkeypatch.setattr(repl_mod, "convert", boom)
        repl._handle_submit("x")
        out = _out(repl)
        assert out.startswith("error:")
        assert "Traceback" not in out
