"""Adapter tests: mode routing to the real engine, and error surfacing."""

import pytest

import converter_engine
from lipika_cli.engine import convert
from lipika_cli.modes import get_mode

SAMPLE = "ଓଡ଼ିଆ ଲିପି"


def test_u2a_routes_to_engine():
    res = convert(get_mode("/u2a"), SAMPLE)
    assert res.text == converter_engine.convert_text(SAMPLE)
    assert (res.n_in, res.n_out) == (len(SAMPLE), len(res.text))
    assert res.fixed is False


def test_a2u_routes_to_engine():
    legacy = converter_engine.convert_text(SAMPLE)
    res = convert(get_mode("/a2u"), legacy)
    assert res.text == converter_engine.convert_akruti_to_unicode(legacy)


def test_u2s_routes_to_engine():
    res = convert(get_mode("/u2s"), SAMPLE)
    assert res.text == converter_engine.convert_text_sreelipi(SAMPLE)


def test_s2u_routes_to_engine():
    legacy = converter_engine.convert_text_sreelipi(SAMPLE)
    res = convert(get_mode("/s2u"), legacy)
    assert res.text == converter_engine.convert_sreelipi_to_unicode(legacy)


def test_fixed_flag_only_affects_u2a_call():
    res = convert(get_mode("/u2a"), "©<", fixed=True)
    assert res.text == converter_engine.convert_text("©<", fix_special_chars=True)


@pytest.mark.parametrize("mode_cmd", ["/u2a", "/a2u", "/u2s", "/s2u"])
def test_non_str_raises_typeerror(mode_cmd):
    with pytest.raises(TypeError):
        convert(get_mode(mode_cmd), 123)  # type: ignore[arg-type]


def test_empty_string_roundtrips():
    for cmd in ("/u2a", "/a2u", "/u2s", "/s2u"):
        res = convert(get_mode(cmd), "")
        assert res.text == ""
