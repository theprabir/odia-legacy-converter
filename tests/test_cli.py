"""Tests for the non-interactive CLI (Phase 4).

Run through main() with real engine; file I/O via tmp_path.
"""

from __future__ import annotations

import io

import pytest

from lipika_cli.cli import main
from lipika_cli.encoding import decode_legacy

SAMPLE = "ନମସ୍କାର ପରୀକ୍ଷା"


def run(capsys, *argv):
    code = main(list(argv))
    captured = capsys.readouterr()
    return code, captured


class TestArgumentConversion:
    def test_u2a_text_argument(self, capsys):
        code, cap = run(capsys, "u2a", SAMPLE)
        assert code == 0
        legacy = cap.out
        # legacy bytes survive the UTF-8 stdout round trip
        from converter_engine import convert_text

        assert legacy == convert_text(SAMPLE)

    def test_a2u_pipe_roundtrip(self, capsys, monkeypatch):
        from converter_engine import convert_text

        legacy = convert_text(SAMPLE)
        monkeypatch.setattr(
            "sys.stdin", io.TextIOWrapper(io.BytesIO(legacy.encode("cp1252")), "cp1252")
        )
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        code, cap = run(capsys, "a2u")
        assert code == 0
        assert cap.out == SAMPLE

    def test_empty_input_fails_cleanly(self, capsys, monkeypatch):
        monkeypatch.setattr("sys.stdin", io.StringIO(""))
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        code, cap = run(capsys, "u2a")
        assert code == 1
        assert "empty input" in cap.err

    def test_no_input_message(self, capsys, monkeypatch):
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        with pytest.raises(SystemExit) as excinfo:
            run(capsys, "u2a")
        assert "no input" in str(excinfo.value)


class TestFileIO:
    def test_utf8_file_in(self, capsys, tmp_path):
        f = tmp_path / "in.txt"
        f.write_text(SAMPLE, encoding="utf-8")
        code, cap = run(capsys, "u2a", "-f", str(f))
        assert code == 0
        from converter_engine import convert_text

        assert cap.out == convert_text(SAMPLE)

    def test_legacy_file_in(self, capsys, tmp_path):
        from converter_engine import convert_text

        f = tmp_path / "legacy.txt"
        f.write_bytes(convert_text(SAMPLE).encode("cp1252"))
        code, cap = run(capsys, "a2u", "-f", str(f))
        assert code == 0
        assert cap.out == SAMPLE

    def test_out_file_cp1252(self, tmp_path):
        out = tmp_path / "out.txt"
        code = main(["u2a", SAMPLE, "-o", str(out)])
        assert code == 0
        from converter_engine import convert_text

        assert out.read_bytes() == convert_text(SAMPLE).encode("cp1252")

    def test_out_file_sreelipi(self, tmp_path):
        from converter_engine import convert_text_sreelipi

        out = tmp_path / "out.txt"
        code = main(["u2s", SAMPLE, "-o", str(out)])
        assert code == 0
        assert out.read_bytes() == convert_text_sreelipi(SAMPLE).encode("cp1252")

    def test_unicode_out_defaults_utf8(self, tmp_path):
        out = tmp_path / "out.txt"
        code = main(["a2u", "IWÿò@û", "-o", str(out)])
        assert code == 0
        assert out.read_text(encoding="utf-8") == "ଓଡ଼ିଆ"

    def test_missing_file_one_line_error(self, capsys):
        code, cap = run(capsys, "u2a", "-f", "_no_such_file.txt")
        assert code == 1
        assert cap.err.startswith("error:")
        assert "--debug" in cap.err

    def test_missing_file_debug_raises(self, capsys):
        # argparse errors exit 2 via SystemExit; our file error is OSError.
        with pytest.raises(SystemExit) as excinfo:
            main(["u2a", "-f", "_no_such_file.txt", "--debug"])
        assert excinfo.value.code != 0 or excinfo.value.code is None


class TestFixedFlag:
    def test_fixed_u2a_bytes(self, capsys):
        code, cap = run(capsys, "u2a", "--fixed", "ତ୍ତ")
        assert code == 0
        # \x8f encoded as UTF-8 on stdout (0xc2 0x8f)
        assert cap.out.encode("utf-8") == b"\xc2\x8f"

    def test_fixed_ignored_elsewhere(self, capsys):
        code, cap = run(capsys, "a2u", "--fixed", "IWÿò@û")
        assert code == 0
        assert "--fixed only applies" in cap.err

    def test_fixed_out_uses_latin1(self, tmp_path):
        out = tmp_path / "fixed.txt"
        code = main(["u2a", "--fixed", "ତ୍ତ", "-o", str(out)])
        assert code == 0
        assert out.read_bytes() == b"\x8f"

    def test_encoding_override(self, tmp_path):
        out = tmp_path / "out.txt"
        code = main(["u2a", "--fixed", "--encoding", "latin-1", "ତ୍ତ", "-o", str(out)])
        assert code == 0
        assert out.read_bytes() == b"\x8f"

    def test_unencodable_out_warns_and_substitutes(self, capsys, tmp_path):
        # fixed u2a output has C1 which cp1252 cannot encode
        out = tmp_path / "out.txt"
        code, cap = run(capsys, "u2a", "--fixed", "--encoding", "cp1252", "ତ୍ତ", "-o", str(out))
        assert code == 0
        assert "not encodable" in cap.err
        assert out.read_bytes() == b"?"


class TestVersionAndHelp:
    def test_version(self, capsys):
        code, cap = run(capsys, "--version")
        assert code == 0
        assert "lipika 0." in cap.out

    def test_help_lists_modes(self, capsys):
        with pytest.raises(SystemExit) as excinfo:
            run(capsys, "--help")
        assert excinfo.value.code in (0, None)
        out = capsys.readouterr().out
        for name in ("u2a", "a2u", "u2s", "s2u"):
            assert name in out


class TestLegacyDecodeHelper:
    def test_decode_c1_fallback_still_holds(self):
        raw = bytes([0x81, 0x8D, 0x8F, 0x90, 0x9D])
        text = decode_legacy(raw)
        assert [ord(c) for c in text] == [0x81, 0x8D, 0x8F, 0x90, 0x9D]
