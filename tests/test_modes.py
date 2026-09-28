"""Tests for the mode registry."""

import pytest

from lipika_cli.modes import DEFAULT_COMMAND, MODES, get_mode


def test_four_modes_registered():
    assert set(MODES) == {"/u2a", "/a2u", "/u2s", "/s2u"}


def test_default_mode_is_u2a():
    assert DEFAULT_COMMAND == "/u2a"
    assert get_mode("/u2a") is not None


def test_labels_match_spec():
    assert get_mode("/u2a").label == "Unicode → Akruti"
    assert get_mode("/a2u").label == "Akruti → Unicode"
    assert get_mode("/u2s").label == "Unicode → Sreelipi"
    assert get_mode("/s2u").label == "Sreelipi → Unicode"


def test_output_encoding_hypotheses():
    assert get_mode("/u2a").output_encoding(fixed=False) == "cp1252"
    assert get_mode("/u2a").output_encoding(fixed=True) == "latin-1"
    assert get_mode("/u2s").output_encoding(fixed=False) == "cp1252"
    for cmd in ("/a2u", "/s2u"):
        assert get_mode(cmd).output_encoding(fixed=True) == "utf-8"


def test_unknown_mode_is_none():
    assert get_mode("/nope") is None


def test_mode_is_frozen():
    with pytest.raises(AttributeError):
        get_mode("/u2a").label = "x"
