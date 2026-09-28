"""Tests for input parsing (pure logic, per AGENTS.md testing rules)."""

from lipika_cli.commands import (
    Command,
    Help,
    Ignore,
    Message,
    Quit,
    Unknown,
    parse,
)


class TestHelpTriggers:
    def test_exact_triggers(self):
        for raw in ("h", "/h", "/help", "?"):
            assert isinstance(parse(raw), Help), raw

    def test_whitespace_trimmed(self):
        assert isinstance(parse("  h  "), Help)
        assert isinstance(parse("\t?\n"), Help)

    def test_embedded_h_is_a_message(self):
        assert isinstance(parse("oh"), Message)
        assert isinstance(parse("h help"), Message)


class TestMessages:
    def test_plain_text(self):
        parsed = parse("ନମସ୍କାର")
        assert isinstance(parsed, Message)

    def test_text_with_slash_not_at_start_is_message(self):
        assert isinstance(parse("path/to file"), Message)

    def test_empty_ignored(self):
        assert isinstance(parse(""), Ignore)
        assert isinstance(parse("   \n "), Ignore)


class TestSlashCommands:
    def test_mode_commands(self):
        for name in ("/u2a", "/a2u", "/u2s", "/s2u"):
            assert parse(name) == Command(name=name)

    def test_mode_command_with_trailing_text_takes_first_token(self):
        # "/u2a some text" - the command token wins; rest is the arg slot
        assert parse("/u2a hello") == Command(name="/u2a", arg="hello")

    def test_quit_variants(self):
        assert isinstance(parse("/quit"), Quit)
        assert isinstance(parse("/exit"), Quit)

    def test_known_output_commands(self):
        assert parse("/fix") == Command(name="/fix")
        assert parse("/copy") == Command(name="/copy")
        assert parse("/save docs.txt") == Command(name="/save", arg="docs.txt")
        assert parse("/save") == Command(name="/save")
        assert parse("/clear") == Command(name="/clear")

    def test_unknown_command(self):
        parsed = parse("/nope")
        assert isinstance(parsed, Unknown)
        assert parsed.name == "/nope"

    def test_unknown_command_leaves_rest_unconverted(self):
        # Unknown command must not convert anything: it returns Unknown,
        # never Message.
        assert isinstance(parse("/nope ନମସ୍କାର"), Unknown)

    def test_case_sensitive(self):
        assert isinstance(parse("/U2A"), Unknown)
